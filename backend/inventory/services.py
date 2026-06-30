"""Lógica de inventario: aplicar movimientos con costeo promedio ponderado.

Todo cambio de existencia pasa por aquí. Cada operación es atómica y bloquea
la variante y el nivel de stock para evitar condiciones de carrera.
"""
from decimal import Decimal

from django.db import models, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from catalog.models import ProductVariant
from geo.geocoding import coords_from_map_url, geocode

from .models import (
    INBOUND_TYPES,
    MovementReason,
    MovementType,
    StockLevel,
    StockMovement,
    Transfer,
    TransferItem,
    TransferStatus,
    Warehouse,
)


def resolve_warehouse_coords(warehouse, *, force=False):
    """Fija (y guarda) las coordenadas de la bodega para el ruteo por cercanía.

    Las toma del enlace de Google Maps si lo hay; si no, geocodifica su ciudad/
    dirección. Best-effort: si no se resuelven, quedan nulas. No reconsulta si ya
    tiene coordenadas (salvo `force`), para no llamar a OpenStreetMap de más.
    """
    if not force and warehouse.latitude is not None and warehouse.longitude is not None:
        return warehouse.latitude, warehouse.longitude
    coords = coords_from_map_url(warehouse.map_embed_url)
    if not coords and warehouse.city_id:
        parts = [
            warehouse.address, warehouse.city.name,
            warehouse.city.department.name, warehouse.city.department.country.name,
        ]
        coords = geocode(', '.join(p for p in parts if p))
    if coords and (warehouse.latitude, warehouse.longitude) != coords:
        warehouse.latitude, warehouse.longitude = coords
        warehouse.save(update_fields=['latitude', 'longitude', 'updated_at'])
    return coords


class InventoryError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Movimiento de inventario inválido.'
    default_code = 'invalid_movement'


class InsufficientStock(InventoryError):
    default_detail = 'No hay existencia suficiente para esta salida.'
    default_code = 'insufficient_stock'


def _level(variant, warehouse):
    """Devuelve (creando si hace falta) el nivel de stock, bloqueado para update."""
    StockLevel.objects.get_or_create(variant=variant, warehouse=warehouse)
    return StockLevel.objects.select_for_update().get(
        variant=variant, warehouse=warehouse
    )


@transaction.atomic
def record_movement(
    *,
    variant,
    warehouse,
    type,
    quantity,
    unit_cost=None,
    reason='',
    note='',
    reference='',
    warehouse_to=None,
    user=None,
):
    """Aplica un movimiento y devuelve el/los StockMovement creados.

    - entrada / ajuste_entrada: suman; la entrada recalcula el costo promedio.
    - salida / ajuste_salida: restan; usan el costo promedio vigente. No dejan
      la existencia en negativo.
    - transferencia: resta en `warehouse` y suma en `warehouse_to` (mismo costo);
      crea dos asientos enlazados por `reference`.
    """
    if quantity is None or quantity <= 0:
        raise InventoryError('La cantidad debe ser mayor a cero.')

    variant = ProductVariant.objects.select_for_update().get(pk=variant.pk)

    if type == MovementType.TRANSFER:
        return _transfer(variant, warehouse, warehouse_to, quantity, note, reference, user)

    level = _level(variant, warehouse)

    if type in INBOUND_TYPES:
        if type == MovementType.ENTRY:
            # La entrada lleva costo de compra y recalcula el promedio ponderado.
            cost = Decimal(unit_cost if unit_cost is not None else variant.average_cost)
            new_total = variant.stock + quantity
            if new_total > 0:
                variant.average_cost = (
                    variant.stock * variant.average_cost + quantity * cost
                ) / new_total
        else:
            # Ajuste de entrada: usa el promedio vigente (no aporta costo nuevo).
            cost = variant.average_cost
        level.quantity += quantity
        variant.stock += quantity
    else:
        # Salidas y ajustes de salida: al costo promedio, sin dejar negativo.
        if quantity > level.quantity:
            raise InsufficientStock(
                f'Solo hay {level.quantity} unidad(es) en {warehouse.name}.'
            )
        cost = variant.average_cost
        level.quantity -= quantity
        variant.stock -= quantity

    level.save(update_fields=['quantity'])
    variant.save(update_fields=['stock', 'average_cost'])

    return StockMovement.objects.create(
        variant=variant,
        warehouse=warehouse,
        type=type,
        reason=reason,
        quantity=quantity,
        unit_cost=cost,
        total_cost=Decimal(cost) * quantity,
        balance_after=level.quantity,
        note=note,
        reference=reference,
        created_by=user,
    )


def _transfer(variant, origin, destination, quantity, note, reference, user):
    if destination is None:
        raise InventoryError('La transferencia necesita una bodega destino.')
    if origin.pk == destination.pk:
        raise InventoryError('La bodega origen y destino no pueden ser la misma.')

    origin_level = _level(variant, origin)
    if quantity > origin_level.quantity:
        raise InsufficientStock(
            f'Solo hay {origin_level.quantity} unidad(es) en {origin.name}.'
        )
    dest_level = _level(variant, destination)
    cost = variant.average_cost  # la transferencia no cambia el costo

    origin_level.quantity -= quantity
    dest_level.quantity += quantity
    origin_level.save(update_fields=['quantity'])
    dest_level.save(update_fields=['quantity'])
    # El total de la variante no cambia (solo cambia de ubicación).

    out_move = StockMovement.objects.create(
        variant=variant,
        warehouse=origin,
        warehouse_to=destination,
        type=MovementType.TRANSFER,
        reason=MovementReason.TRANSFER,
        quantity=quantity,
        unit_cost=cost,
        total_cost=Decimal(cost) * quantity,
        balance_after=origin_level.quantity,
        note=note,
        reference=reference,
        created_by=user,
    )
    StockMovement.objects.create(
        variant=variant,
        warehouse=destination,
        type=MovementType.TRANSFER,
        reason=MovementReason.TRANSFER,
        quantity=quantity,
        unit_cost=cost,
        total_cost=Decimal(cost) * quantity,
        balance_after=dest_level.quantity,
        note=note,
        reference=reference,
        created_by=user,
    )
    # Devolvemos el asiento de salida (origen) como representante.
    return out_move


# ----------------------- Transferencias con aprobación -----------------------
# A diferencia de `_transfer` (inmediata), aquí el traslado se hace en dos pasos:
# al solicitar la existencia SALE de origen (reserva / en tránsito) y solo entra
# al destino cuando el jefe del punto destino la acepta. Cada paso es un asiento
# del kardex (append-only): nada se borra, todo queda como registro.


class TransferError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'No se pudo procesar la transferencia.'
    default_code = 'invalid_transfer'


def _next_transfer_number():
    last = Transfer.objects.aggregate(m=models.Max('number'))['m'] or 0
    return last + 1


def _move_in(variant, warehouse, quantity, cost, *, reference, note, user, type, reason):
    """Suma `quantity` a una bodega y deja el asiento del kardex (sin tocar costo)."""
    level = _level(variant, warehouse)
    level.quantity += quantity
    variant.stock += quantity
    level.save(update_fields=['quantity'])
    variant.save(update_fields=['stock'])
    StockMovement.objects.create(
        variant=variant, warehouse=warehouse, type=type, reason=reason,
        quantity=quantity, unit_cost=cost, total_cost=Decimal(cost) * quantity,
        balance_after=level.quantity, reference=reference, note=note, created_by=user,
    )


@transaction.atomic
def request_transfer(*, origin, destination, lines, note='', user=None):
    """Crea una transferencia PENDIENTE y reserva el stock (lo saca de origen).

    `lines`: [{variant, quantity}]. Valida existencia en origen y registra, por
    cada línea, un asiento de salida (transferencia) en la bodega origen.
    """
    if origin.pk == destination.pk:
        raise TransferError('La bodega origen y destino no pueden ser la misma.')
    if not lines:
        raise TransferError('La transferencia no tiene productos.')

    transfer = Transfer.objects.create(
        number=_next_transfer_number(),
        origin=origin,
        destination=destination,
        status=TransferStatus.PENDING,
        note=note,
        requested_by=user,
    )
    reference = f'Transferencia #{transfer.number}'
    seen = set()
    for line in lines:
        variant = ProductVariant.objects.select_for_update().get(pk=line['variant'].pk)
        if variant.pk in seen:
            raise TransferError('Hay una variante repetida en la transferencia.')
        seen.add(variant.pk)
        quantity = int(line['quantity'])
        if quantity <= 0:
            raise TransferError('Cada línea debe tener cantidad mayor a cero.')

        origin_level = _level(variant, origin)
        if quantity > origin_level.quantity:
            raise InsufficientStock(
                f'Solo hay {origin_level.quantity} unidad(es) de {variant.sku} en {origin.name}.'
            )
        cost = variant.average_cost
        origin_level.quantity -= quantity
        variant.stock -= quantity
        origin_level.save(update_fields=['quantity'])
        variant.save(update_fields=['stock'])

        TransferItem.objects.create(
            transfer=transfer, variant=variant, quantity=quantity, unit_cost=cost
        )
        StockMovement.objects.create(
            variant=variant, warehouse=origin, warehouse_to=destination,
            type=MovementType.TRANSFER, reason=MovementReason.TRANSFER,
            quantity=quantity, unit_cost=cost, total_cost=Decimal(cost) * quantity,
            balance_after=origin_level.quantity, reference=reference, note=note,
            created_by=user,
        )
    return transfer


@transaction.atomic
def accept_transfer(transfer, *, user=None):
    """Acepta una transferencia pendiente: la existencia entra a la bodega destino."""
    transfer = Transfer.objects.select_for_update().get(pk=transfer.pk)
    if not transfer.is_pending:
        raise TransferError('La transferencia ya fue resuelta.')

    reference = f'Transferencia #{transfer.number}'
    for item in transfer.items.select_related('variant'):
        variant = ProductVariant.objects.select_for_update().get(pk=item.variant_id)
        _move_in(
            variant, transfer.destination, item.quantity, item.unit_cost,
            reference=reference, note=transfer.note, user=user,
            type=MovementType.TRANSFER, reason=MovementReason.TRANSFER,
        )
    transfer.status = TransferStatus.ACCEPTED
    transfer.resolved_by = user
    transfer.resolved_at = timezone.now()
    transfer.save(update_fields=['status', 'resolved_by', 'resolved_at', 'updated_at'])
    return transfer


@transaction.atomic
def _undo_transfer(transfer, *, user, new_status):
    """Devuelve la existencia reservada a la bodega origen (rechazo o cancelación)."""
    transfer = Transfer.objects.select_for_update().get(pk=transfer.pk)
    if not transfer.is_pending:
        raise TransferError('La transferencia ya fue resuelta.')

    reference = f'Transferencia #{transfer.number} ({TransferStatus(new_status).label.lower()})'
    for item in transfer.items.select_related('variant'):
        variant = ProductVariant.objects.select_for_update().get(pk=item.variant_id)
        _move_in(
            variant, transfer.origin, item.quantity, item.unit_cost,
            reference=reference, note=transfer.note, user=user,
            type=MovementType.ADJUST_IN, reason=MovementReason.TRANSFER,
        )
    transfer.status = new_status
    transfer.resolved_by = user
    transfer.resolved_at = timezone.now()
    transfer.save(update_fields=['status', 'resolved_by', 'resolved_at', 'updated_at'])
    return transfer


def reject_transfer(transfer, *, user=None):
    """Rechaza la transferencia (jefe destino): la existencia vuelve a origen."""
    return _undo_transfer(transfer, user=user, new_status=TransferStatus.REJECTED)


def cancel_transfer(transfer, *, user=None):
    """Cancela la transferencia (solicitante): la existencia vuelve a origen."""
    return _undo_transfer(transfer, user=user, new_status=TransferStatus.CANCELLED)
