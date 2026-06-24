/**
 * Tipos de identificación admitidos (coinciden con User.IdType del backend).
 * Compartido por registro, perfil, usuarios y clientes.
 */
export const ID_TYPES = [
  { value: 'CC', label: 'Cédula de ciudadanía (CC)' },
  { value: 'CE', label: 'Cédula de extranjería (CE)' },
  { value: 'NIT', label: 'NIT' },
  { value: 'PP', label: 'Pasaporte (PP)' },
  { value: 'TI', label: 'Tarjeta de identidad (TI)' }
]
