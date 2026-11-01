import { api, errorMessage } from "@/lib/api";

export const FILE_KINDS = { all: "Todos os arquivos", document: "Documentos", image: "Imagens", video: "Vídeos", audio: "Áudios" };

export function formatSize(bytes = 0) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} KB`;
  return `${(bytes / (1024 * 1024)).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} MB`;
}

export async function fileError(error) {
  if (error.response?.data instanceof Blob) {
    try { return JSON.parse(await error.response.data.text()).detail || "Não foi possível abrir o arquivo."; }
    catch (_) { return "Não foi possível abrir o arquivo. Tente novamente."; }
  }
  return errorMessage(error);
}

export async function downloadFile(file) {
  const { data } = await api.get(`/files/${file.id}/download`, { responseType: "blob" });
  const url = URL.createObjectURL(data);
  const link = Object.assign(document.createElement("a"), { href: url, download: file.original_filename });
  document.body.appendChild(link);
  link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}