import { lazy, Suspense, useEffect, useState } from "react";
import { Download, FileText } from "lucide-react";
import { api } from "@/lib/api";
import { fileError, formatSize } from "@/lib/files";
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/components/ui/dialog";

const PdfPreview = lazy(() => import("@/components/files/PdfPreview"));

export const FilePreview = ({ file, onClose, onDownload, downloading, downloadError }) => {
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const [loading, setLoading] = useState(true);
  const supported = file && (file.kind !== "document" || ["application/pdf", "text/plain", "text/csv", "application/json"].includes(file.content_type));

  useEffect(() => {
    if (!file || !supported) return;
    const controller = new AbortController();
    let url;
    setPreview(null); setError(""); setLoading(true);
    api.get(`/files/${file.id}/download`, { responseType: "blob", signal: controller.signal }).then(async ({ data }) => {
      if (controller.signal.aborted) return;
      if (file.content_type.startsWith("text/") || file.content_type === "application/json") {
        const text = await data.slice(0, 200000).text();
        if (!controller.signal.aborted) setPreview({ text, truncated: data.size > 200000 });
      } else if (file.content_type === "application/pdf") { setPreview({ blob: data }); }
      else { url = URL.createObjectURL(data); setPreview({ url }); }
    }).catch(async (e) => { if (!controller.signal.aborted) setError(await fileError(e)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => { controller.abort(); if (url) URL.revokeObjectURL(url); };
  }, [file, supported, retry]);

  return <Dialog open={!!file} onOpenChange={(open) => { if (!open) onClose(); }}>
    <DialogContent className="glass-strong file-dialog sm:max-w-3xl" data-testid="file-preview-dialog">
      <DialogTitle className="font-display pr-6 break-all !tracking-normal" data-testid="file-preview-title">{file?.original_filename}</DialogTitle>
      <DialogDescription className="text-slate-400" data-testid="file-preview-details">{formatSize(file?.size)} · Arquivo privado</DialogDescription>
      <div className="file-preview-content" data-testid="file-preview-content">
        {!supported ? <div className="text-center py-12 text-slate-400" data-testid="file-preview-unsupported"><FileText size={36} className="mx-auto mb-3 text-blue-300" /><p>Prévia indisponível para este formato.</p></div>
          : loading ? <div className="spinner mx-auto my-14" role="status" aria-label="Carregando prévia" data-testid="file-preview-loading" />
          : error ? <div className="py-10 text-center" role="alert" data-testid="file-preview-error"><p className="text-red-300 mb-4">{error}</p><button className="btn-ghost" onClick={() => setRetry(retry + 1)} data-testid="file-preview-retry">Tentar novamente</button></div>
          : preview?.text !== undefined ? <><pre className="whitespace-pre-wrap break-words text-sm p-4" data-testid="file-preview-text">{preview.text}</pre>{preview.truncated && <p className="text-xs text-amber-300 p-4" data-testid="file-preview-truncated">Prévia parcial. Baixe o arquivo para ver o conteúdo completo.</p>}</>
          : preview?.blob ? <Suspense fallback={<p className="p-6 text-sm text-blue-200" role="status" data-testid="file-pdf-module-loading">Carregando leitor…</p>}><PdfPreview blob={preview.blob} /></Suspense>
          : preview?.url && (file.kind === "image" ? <img src={preview.url} alt={file.original_filename} className="file-preview-image" data-testid="file-preview-image" onError={() => setError("Não foi possível exibir esta imagem. O arquivo ainda pode ser baixado.")} />
            : file.kind === "video" ? <video controls playsInline src={preview.url} className="file-preview-video" data-testid="file-preview-video" onError={() => setError("Este vídeo não pode ser reproduzido no navegador. Baixe o arquivo para abri-lo.")} />
            : file.kind === "audio" ? <audio controls src={preview.url} className="w-full my-8" data-testid="file-preview-audio" onError={() => setError("Este áudio não pode ser reproduzido no navegador. Baixe o arquivo para abri-lo.")} />
            : null)}
      </div>
      {downloadError && <p role="alert" className="text-sm text-red-300" data-testid="file-preview-download-error">{downloadError} Tente baixar novamente.</p>}
      <div className="flex justify-end"><button className="btn-primary" disabled={downloading} onClick={() => onDownload(file)} data-testid="file-preview-download"><Download size={17} />{downloading ? "Baixando…" : "Baixar arquivo"}</button></div>
    </DialogContent>
  </Dialog>;
};

export const FileDeleteDialog = ({ file, onClose, onConfirm, busy, error }) => (
  <Dialog open={!!file} onOpenChange={(open) => { if (!open && !busy) onClose(); }}>
    <DialogContent className="glass-strong file-dialog" data-testid="file-delete-dialog" onEscapeKeyDown={(e) => busy && e.preventDefault()} onPointerDownOutside={(e) => busy && e.preventDefault()}>
      <DialogTitle className="font-display !tracking-normal" data-testid="file-delete-title">Excluir arquivo?</DialogTitle>
      <DialogDescription className="text-slate-300 break-all" data-testid="file-delete-description">“{file?.original_filename}” será removido da biblioteca e não poderá mais ser acessado pelo aplicativo. O conteúdo pode permanecer no armazenamento do serviço.</DialogDescription>
      {error && <p role="alert" className="text-sm text-red-300" data-testid="file-delete-error">{error}</p>}
      <div className="flex justify-end gap-3 mt-2">
        <button className="btn-ghost" disabled={busy} onClick={onClose} data-testid="file-delete-cancel">Cancelar</button>
        <button className="btn-danger disabled:opacity-50" disabled={busy} onClick={onConfirm} data-testid="file-delete-confirm">{busy ? "Excluindo…" : "Excluir arquivo"}</button>
      </div>
    </DialogContent>
  </Dialog>
);