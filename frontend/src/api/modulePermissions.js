import request from '../utils/request'

export function getModulePermissionsStructure() {
  return request.get('/api/v1/module-permissions/structure')
}
export function setModuleRoles(moduleKey, roles) {
  return request.put(`/api/v1/module-permissions/${moduleKey}`, { roles })
}
export function resetModulePermissions() {
  return request.post('/api/v1/module-permissions/reset')
}
