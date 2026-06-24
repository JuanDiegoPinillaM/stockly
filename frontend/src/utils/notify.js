import Swal from 'sweetalert2'

/**
 * Helpers de notificación centralizados (SweetAlert2).
 * - toastSuccess/toastError: avisos no intrusivos arriba a la derecha.
 * - confirmAction/confirmDelete: diálogos de confirmación.
 */

const PRIMARY = '#4f46e5'
const DANGER = '#dc2626'
const GRAY = '#94a3b8'

const toast = Swal.mixin({
  toast: true,
  position: 'top-end',
  showConfirmButton: false,
  timer: 2800,
  timerProgressBar: true,
  didOpen: (el) => {
    el.addEventListener('mouseenter', Swal.stopTimer)
    el.addEventListener('mouseleave', Swal.resumeTimer)
  }
})

export function toastSuccess(title) {
  return toast.fire({ icon: 'success', title })
}

export function toastError(title) {
  return toast.fire({ icon: 'error', title })
}

export async function confirmAction({
  title = '¿Confirmar?',
  text = '',
  confirmText = 'Sí, continuar',
  icon = 'question'
} = {}) {
  const res = await Swal.fire({
    title,
    text,
    icon,
    showCancelButton: true,
    confirmButtonText: confirmText,
    cancelButtonText: 'Cancelar',
    confirmButtonColor: PRIMARY,
    cancelButtonColor: GRAY,
    reverseButtons: true
  })
  return res.isConfirmed
}

export async function confirmDelete(text = 'Esta acción no se puede deshacer.') {
  const res = await Swal.fire({
    title: '¿Eliminar?',
    text,
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Sí, eliminar',
    cancelButtonText: 'Cancelar',
    confirmButtonColor: DANGER,
    cancelButtonColor: GRAY,
    reverseButtons: true
  })
  return res.isConfirmed
}
