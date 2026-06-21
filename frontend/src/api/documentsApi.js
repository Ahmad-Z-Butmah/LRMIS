// Placeholder API — logic will be implemented in Phase 1+
const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function getDocumentsByApplication(applicationId) {}

export async function uploadDocument(applicationId, formData) {}

export async function reviewDocument(documentId, status) {}

export async function deleteDocument(documentId) {}
