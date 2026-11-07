const DB_NAME = 'cryptavault-portal';
const DB_VERSION = 1;

export const STORES = [
  'vault',
  'files',
  'blobs',
  'shares',
  'threads',
  'messages',
  'audit',
] as const;

export type StoreName = (typeof STORES)[number];

let dbPromise: Promise<IDBDatabase> | null = null;

export function getDb(): Promise<IDBDatabase> {
  if (dbPromise) return dbPromise;
  dbPromise = new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains('vault')) {
        db.createObjectStore('vault', { keyPath: 'key' });
      }
      if (!db.objectStoreNames.contains('files')) {
        db.createObjectStore('files', { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains('blobs')) {
        db.createObjectStore('blobs', { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains('shares')) {
        db.createObjectStore('shares', { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains('threads')) {
        db.createObjectStore('threads', { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains('messages')) {
        const store = db.createObjectStore('messages', { keyPath: 'id' });
        store.createIndex('threadId', 'threadId', { unique: false });
      }
      if (!db.objectStoreNames.contains('audit')) {
        const store = db.createObjectStore('audit', { keyPath: 'id' });
        store.createIndex('at', 'at', { unique: false });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error('Failed to open IndexedDB.'));
  });
  return dbPromise;
}

function requestToPromise<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error('IndexedDB request failed.'));
  });
}

function transactionDone(tx: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error ?? new Error('IndexedDB transaction failed.'));
    tx.onabort = () => reject(tx.error ?? new Error('IndexedDB transaction aborted.'));
  });
}

export async function dbGet<T>(store: StoreName, key: IDBValidKey): Promise<T | undefined> {
  const db = await getDb();
  const tx = db.transaction(store, 'readonly');
  const result = await requestToPromise(tx.objectStore(store).get(key));
  return result as T | undefined;
}

export async function dbGetAll<T>(store: StoreName): Promise<T[]> {
  const db = await getDb();
  const tx = db.transaction(store, 'readonly');
  const result = await requestToPromise(tx.objectStore(store).getAll());
  return result as T[];
}

export async function dbGetByIndex<T>(
  store: StoreName,
  indexName: string,
  value: IDBValidKey,
): Promise<T[]> {
  const db = await getDb();
  const tx = db.transaction(store, 'readonly');
  const result = await requestToPromise(tx.objectStore(store).index(indexName).getAll(value));
  return result as T[];
}

export async function dbPut<T>(store: StoreName, value: T): Promise<void> {
  const db = await getDb();
  const tx = db.transaction(store, 'readwrite');
  tx.objectStore(store).put(value);
  await transactionDone(tx);
}

export async function dbPutMany<T>(store: StoreName, values: T[]): Promise<void> {
  if (values.length === 0) return;
  const db = await getDb();
  const tx = db.transaction(store, 'readwrite');
  const objectStore = tx.objectStore(store);
  for (const value of values) objectStore.put(value);
  await transactionDone(tx);
}

export async function dbDelete(store: StoreName, key: IDBValidKey): Promise<void> {
  const db = await getDb();
  const tx = db.transaction(store, 'readwrite');
  tx.objectStore(store).delete(key);
  await transactionDone(tx);
}

export async function dbClear(store: StoreName): Promise<void> {
  const db = await getDb();
  const tx = db.transaction(store, 'readwrite');
  tx.objectStore(store).clear();
  await transactionDone(tx);
}

export async function dbExportAll(): Promise<Record<StoreName, unknown[]>> {
  const result = {} as Record<StoreName, unknown[]>;
  for (const store of STORES) {
    result[store] = await dbGetAll<unknown>(store);
  }
  return result;
}

export async function dbImportAll(data: Record<string, unknown[]>): Promise<void> {
  for (const store of STORES) {
    await dbClear(store);
  }
  for (const store of STORES) {
    const values = data[store];
    if (Array.isArray(values)) {
      await dbPutMany(store, values);
    }
  }
}

export async function deleteDatabase(): Promise<void> {
  const db = await getDb();
  db.close();
  dbPromise = null;
  await new Promise<void>((resolve, reject) => {
    const request = indexedDB.deleteDatabase(DB_NAME);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error ?? new Error('Failed to delete vault.'));
    request.onblocked = () => resolve();
  });
}

export function resetDbConnection(): void {
  dbPromise = null;
}
