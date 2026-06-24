from rest_framework.views import exception_handler as drf_exception_handler


def _first_error(data):
    for value in data.values():
        if isinstance(value, list) and value:
            return str(value[0])
        if isinstance(value, str):
            return value
    return None


def custom_exception_handler(exc, context):
    """Normaliza todas las respuestas de error a un contrato uniforme:

        {
          "detail": "mensaje legible para el usuario",
          "code":   "codigo_maquina" | null,
          "errors": { "campo": ["..."] } | null
        }
    """
    response = drf_exception_handler(exc, context)
    if response is None:
        return response

    data = response.data
    detail = None
    code = None
    errors = None

    if isinstance(data, dict) and 'detail' in data and not isinstance(data['detail'], (list, dict)):
        # Excepción simple de API (auth, throttling, 404, permisos…).
        detail = str(data['detail'])
        code = getattr(data['detail'], 'code', None)
    elif isinstance(data, dict):
        # Errores de validación por campo.
        errors = data
        code = 'validation_error'
        detail = _first_error(data) or 'Revisa los datos del formulario.'
    elif isinstance(data, list):
        errors = {'non_field_errors': [str(x) for x in data]}
        code = 'validation_error'
        detail = str(data[0]) if data else 'Solicitud inválida.'

    response.data = {'detail': detail, 'code': code, 'errors': errors}
    return response
