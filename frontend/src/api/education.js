import request from '../utils/request'

const P = '/api/v1/education'

// A. 人员档案
export function listPersonnel(params) { return request.get(`${P}/personnel`, { params }) }
export function getPersonnel(id) { return request.get(`${P}/personnel/${id}`) }
export function createPersonnel(data) { return request.post(`${P}/personnel`, data) }
export function updatePersonnel(id, data) { return request.put(`${P}/personnel/${id}`, data) }
export function deletePersonnel(id) { return request.delete(`${P}/personnel/${id}`) }

// 人员档案子表（按 person_id 过滤）
export function listPersonnelChild(path, params) { return request.get(`${P}/${path}`, { params }) }
export function createPersonnelChild(path, data) { return request.post(`${P}/${path}`, data) }
export function updatePersonnelChild(path, id, data) { return request.put(`${P}/${path}/${id}`, data) }
export function deletePersonnelChild(path, id) { return request.delete(`${P}/${path}/${id}`) }

// B. 新员工培训 + 独立上岗认证
export function listNewEmployee(params) { return request.get(`${P}/new-employee-trains`, { params }) }
export function getNewEmployee(id) { return request.get(`${P}/new-employee-trains/${id}`) }
export function createNewEmployee(data) { return request.post(`${P}/new-employee-trains`, data) }
export function updateNewEmployee(id, data) { return request.put(`${P}/new-employee-trains/${id}`, data) }
export function deleteNewEmployee(id) { return request.delete(`${P}/new-employee-trains/${id}`) }

export function listCertAuth(params) { return request.get(`${P}/cert-auths`, { params }) }
export function getCertAuth(id) { return request.get(`${P}/cert-auths/${id}`) }
export function createCertAuth(data) { return request.post(`${P}/cert-auths`, data) }
export function updateCertAuth(id, data) { return request.put(`${P}/cert-auths/${id}`, data) }
export function deleteCertAuth(id) { return request.delete(`${P}/cert-auths/${id}`) }

// C. 能力评估 + 人员比对
export function listCompetency(params) { return request.get(`${P}/competency-assessments`, { params }) }
export function getCompetency(id) { return request.get(`${P}/competency-assessments/${id}`) }
export function createCompetency(data) { return request.post(`${P}/competency-assessments`, data) }
export function updateCompetency(id, data) { return request.put(`${P}/competency-assessments/${id}`, data) }
export function deleteCompetency(id) { return request.delete(`${P}/competency-assessments/${id}`) }

export function listComparison(params) { return request.get(`${P}/personnel-comparisons`, { params }) }
export function getComparison(id) { return request.get(`${P}/personnel-comparisons/${id}`) }
export function createComparison(data) { return request.post(`${P}/personnel-comparisons`, data) }
export function updateComparison(id, data) { return request.put(`${P}/personnel-comparisons/${id}`, data) }
export function deleteComparison(id) { return request.delete(`${P}/personnel-comparisons/${id}`) }

// D/E/F. 培训计划 / 培训记录 / 实习带教
export function listTrainingPlan(params) { return request.get(`${P}/training-plans`, { params }) }
export function getTrainingPlan(id) { return request.get(`${P}/training-plans/${id}`) }
export function createTrainingPlan(data) { return request.post(`${P}/training-plans`, data) }
export function updateTrainingPlan(id, data) { return request.put(`${P}/training-plans/${id}`, data) }
export function deleteTrainingPlan(id) { return request.delete(`${P}/training-plans/${id}`) }

export function listTrainingSession(params) { return request.get(`${P}/training-sessions`, { params }) }
export function getTrainingSession(id) { return request.get(`${P}/training-sessions/${id}`) }
export function createTrainingSession(data) { return request.post(`${P}/training-sessions`, data) }
export function updateTrainingSession(id, data) { return request.put(`${P}/training-sessions/${id}`, data) }
export function deleteTrainingSession(id) { return request.delete(`${P}/training-sessions/${id}`) }

export function listMentor(params) { return request.get(`${P}/internship-mentors`, { params }) }
export function getMentor(id) { return request.get(`${P}/internship-mentors/${id}`) }
export function createMentor(data) { return request.post(`${P}/internship-mentors`, data) }
export function updateMentor(id, data) { return request.put(`${P}/internship-mentors/${id}`, data) }
export function deleteMentor(id) { return request.delete(`${P}/internship-mentors/${id}`) }

export function listScore(params) { return request.get(`${P}/internship-scores`, { params }) }
export function getScore(id) { return request.get(`${P}/internship-scores/${id}`) }
export function createScore(data) { return request.post(`${P}/internship-scores`, data) }
export function updateScore(id, data) { return request.put(`${P}/internship-scores/${id}`, data) }
export function deleteScore(id) { return request.delete(`${P}/internship-scores/${id}`) }

// 附件（照片/签到扫描件/课件/通知/考题/效果评价 等）
export function listEduAttachments(ownerType, ownerId, kind) {
  const params = {}
  if (kind) params.kind = kind
  return request.get(`/api/v1/education-attachments/${ownerType}/${ownerId}`, { params })
}
export function uploadEduAttachments(ownerType, ownerId, kind, files) {
  const fd = new FormData()
  for (const f of files) fd.append('files', f)
  return request.post(`/api/v1/education-attachments/${ownerType}/${ownerId}?kind=${encodeURIComponent(kind || 'other')}`, fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
export function eduAttachmentUrl(id, inline = true) {
  const token = localStorage.getItem('token')
  return `/api/v1/education-attachments/file/${id}${inline ? '?inline=true' : '?inline=false'}${token ? '&token=' + encodeURIComponent(token) : ''}`
}
export function deleteEduAttachment(id) {
  return request.delete(`/api/v1/education-attachments/file/${id}`)
}
