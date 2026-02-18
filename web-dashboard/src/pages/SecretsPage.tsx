import { useState, useEffect, useCallback } from 'react';
import { PlusIcon, TrashIcon, KeyIcon, ChevronDownIcon, ChevronRightIcon } from '@heroicons/react/24/outline';
import { listSecrets, getSecretKeys, upsertSecret, deleteSecretKey, SecretMeta } from '../services/secretsApi';

const PRESET_SECRETS = [
  'exchange-binance-mainnet',
  'exchange-binance-testnet',
  'exchange-bybit-mainnet',
  'exchange-bybit-testnet',
];

export default function SecretsPage() {
  const [secrets, setSecrets] = useState<SecretMeta[]>([]);
  const [expanded, setExpanded] = useState<Record<string, string[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Upload form state
  const [uploadSecret, setUploadSecret] = useState(PRESET_SECRETS[0]);
  const [customName, setCustomName] = useState('');
  const [pairs, setPairs] = useState([{ key: '', value: '' }]);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listSecrets();
      setSecrets(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const toggleExpand = async (name: string) => {
    if (expanded[name]) {
      setExpanded(prev => { const n = { ...prev }; delete n[name]; return n; });
      return;
    }
    try {
      const { keys } = await getSecretKeys(name);
      setExpanded(prev => ({ ...prev, [name]: keys }));
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleDeleteKey = async (secretName: string, key: string) => {
    if (!confirm(`'${secretName}' 에서 키 '${key}'를 삭제할까요?`)) return;
    try {
      await deleteSecretKey(secretName, key);
      setExpanded(prev => ({ ...prev, [secretName]: prev[secretName].filter(k => k !== key) }));
      await load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleUpload = async () => {
    const name = uploadSecret === '__custom__' ? customName.trim() : uploadSecret;
    if (!name) return;
    const validPairs = pairs.filter(p => p.key.trim());
    if (!validPairs.length) return;

    setUploading(true);
    setUploadMsg(null);
    try {
      const data = Object.fromEntries(validPairs.map(p => [p.key.trim(), p.value]));
      const result = await upsertSecret(name, data);
      setUploadMsg({ type: 'ok', text: `${result.action}: ${result.keys.join(', ')}` });
      setPairs([{ key: '', value: '' }]);
      await load();
    } catch (e: any) {
      setUploadMsg({ type: 'err', text: e.message });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Exchange API Keys</h1>

      {/* Upload Form */}
      <div className="bg-gray-800 rounded-lg p-5 space-y-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <PlusIcon className="w-5 h-5" /> KV 업로드
        </h2>

        <div className="flex flex-wrap gap-3">
          <div className="flex-1 min-w-48">
            <label className="block text-xs text-gray-400 mb-1">Secret 이름</label>
            <select
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
              value={uploadSecret}
              onChange={e => setUploadSecret(e.target.value)}
            >
              {PRESET_SECRETS.map(s => <option key={s} value={s}>{s}</option>)}
              <option value="__custom__">직접 입력...</option>
            </select>
          </div>
          {uploadSecret === '__custom__' && (
            <div className="flex-1 min-w-48">
              <label className="block text-xs text-gray-400 mb-1">이름 (exchange- 로 시작)</label>
              <input
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
                placeholder="exchange-..."
                value={customName}
                onChange={e => setCustomName(e.target.value)}
              />
            </div>
          )}
        </div>

        <div className="space-y-2">
          {pairs.map((pair, i) => (
            <div key={i} className="flex gap-2">
              <input
                className="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm font-mono"
                placeholder="KEY (예: API_KEY)"
                value={pair.key}
                onChange={e => setPairs(prev => prev.map((p, j) => j === i ? { ...p, key: e.target.value } : p))}
              />
              <input
                className="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm font-mono"
                type="password"
                placeholder="VALUE"
                value={pair.value}
                onChange={e => setPairs(prev => prev.map((p, j) => j === i ? { ...p, value: e.target.value } : p))}
              />
              {pairs.length > 1 && (
                <button
                  className="text-gray-400 hover:text-red-400"
                  onClick={() => setPairs(prev => prev.filter((_, j) => j !== i))}
                >
                  <TrashIcon className="w-4 h-4" />
                </button>
              )}
            </div>
          ))}
          <button
            className="text-xs text-blue-400 hover:text-blue-300"
            onClick={() => setPairs(prev => [...prev, { key: '', value: '' }])}
          >
            + 키 추가
          </button>
        </div>

        <div className="flex items-center gap-3">
          <button
            className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded text-sm font-medium disabled:opacity-50"
            onClick={handleUpload}
            disabled={uploading}
          >
            {uploading ? '업로드 중...' : '업로드'}
          </button>
          {uploadMsg && (
            <span className={`text-sm ${uploadMsg.type === 'ok' ? 'text-green-400' : 'text-red-400'}`}>
              {uploadMsg.text}
            </span>
          )}
        </div>
      </div>

      {/* Secret List */}
      <div className="bg-gray-800 rounded-lg p-5">
        <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
          <KeyIcon className="w-5 h-5" /> 등록된 Secrets
        </h2>

        {error && <p className="text-red-400 text-sm mb-3">{error}</p>}
        {loading && <p className="text-gray-400 text-sm">불러오는 중...</p>}

        {!loading && secrets.length === 0 && (
          <p className="text-gray-500 text-sm">등록된 exchange- Secret이 없습니다.</p>
        )}

        <div className="space-y-2">
          {secrets.map(s => (
            <div key={s.name} className="border border-gray-700 rounded">
              <button
                className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-700 rounded"
                onClick={() => toggleExpand(s.name)}
              >
                <div className="flex items-center gap-2">
                  {expanded[s.name] ? <ChevronDownIcon className="w-4 h-4" /> : <ChevronRightIcon className="w-4 h-4" />}
                  <span className="font-mono text-sm">{s.name}</span>
                  <span className="text-xs text-gray-400">{s.key_count}개 키</span>
                </div>
                {s.created_at && (
                  <span className="text-xs text-gray-500">
                    {new Date(s.created_at).toLocaleDateString()}
                  </span>
                )}
              </button>

              {expanded[s.name] && (
                <div className="border-t border-gray-700 px-4 py-3 space-y-1">
                  {expanded[s.name].length === 0 && (
                    <p className="text-gray-500 text-xs">키 없음</p>
                  )}
                  {expanded[s.name].map(key => (
                    <div key={key} className="flex items-center justify-between group">
                      <span className="font-mono text-sm text-green-400">{key}</span>
                      <button
                        className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-400 transition-opacity"
                        onClick={() => handleDeleteKey(s.name, key)}
                        title="키 삭제"
                      >
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
