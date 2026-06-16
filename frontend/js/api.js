const API_BASE = "/api";

async function handleResponse(response) {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      if (data && data.detail) {
        detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      }
    } catch (err) {
      // response body was not JSON, keep statusText
    }
    throw new Error(detail);
  }
  if (response.status === 204) return null;
  return response.json();
}

export async function apiGet(path) {
  const response = await fetch(`${API_BASE}${path}`);
  return handleResponse(response);
}

export async function apiPost(path, body) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return handleResponse(response);
}

export async function apiPut(path, body) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return handleResponse(response);
}

export async function apiDelete(path) {
  const response = await fetch(`${API_BASE}${path}`, { method: "DELETE" });
  return handleResponse(response);
}
