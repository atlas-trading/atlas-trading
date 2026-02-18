import { getApiBaseUrl } from './api';

export interface SecretMeta {
  name: string;
  key_count: number;
  created_at: string | null;
}

export interface SecretKeys {
  name: string;
  keys: string[];
}

export async function listSecrets(): Promise<SecretMeta[]> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/k8s-secrets`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getSecretKeys(name: string): Promise<SecretKeys> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/k8s-secrets/${name}/keys`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function upsertSecret(name: string, data: Record<string, string>): Promise<{ action: string; name: string; keys: string[] }> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/k8s-secrets/${name}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function deleteSecretKey(name: string, key: string): Promise<void> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/k8s-secrets/${name}/keys/${key}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(await res.text());
}
