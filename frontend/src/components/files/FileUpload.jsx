import { useRef, useState } from "react";
import { UploadCloud, LoaderCircle } from "lucide-react";
import { toast } from "sonner";
import { api, errorMessage } from "@/lib/api";
import { Progress } from "@/components/ui/progress";
import { formatSize } from "@/lib/files";

export const FileUpload = ({ config, onUploaded }) => {
  const input = useRef(null);
  const lock = useRef(false);
  const [dragging, setDragging] = useState(false);
  const [upload, setUpload] = useState(null);
  const [errors, setErrors] = useState([]);

  const send = async (selection) => {
    if (lock.current || !config) return;
    const files = Array.from(selection || []);
    if (!files.length) return;
    if (files.length > 10) { setErrors(["Envie até 10 arquivos por vez."]); return; }
    lock.current = true; setErrors([]); setDragging(false);
    let completed = 0;
    const failures = [];
    for (let index = 0; index < files.length; index += 1) {
      const file = files[index];
      const ext = `.${file.name.split(".").pop().toLowerCase()}`;
      setUpload({ name: file.name, index: index + 1, total: files.length, progress: 0 });
      if (!config.extensions.includes(ext) || file.size === 0 || file.size > config.max_file_size) {
        failures.push(`${file.name}: ${!config.extensions.includes(ext) ? "formato não permitido" : file.size === 0 ? "arquivo vazio" : `limite de ${formatSize(config.max_file_size)} por arquivo`}.`);
        continue;
      }
      try {
        const body = new FormData(); body.append("file", file);
        await api.post("/files", body, { onUploadProgress: (event) => {
          setUpload((value) => value && { ...value, progress: Math.min(95, Math.round((event.loaded / (event.total || file.size)) * 95)) });
        } });
        completed += 1;
      } catch (error) { failures.push(`${file.name}: ${errorMessage(error)}`); }
    }
    setErrors(failures); setUpload(null); lock.current = false;
    if (completed) { toast.success(`${completed} ${completed === 1 ? "arquivo enviado" : "arquivos enviados"}`); onUploaded(); }
  };

  return (
    <section className={`file-dropzone ${dragging ? "is-dragging" : ""}`} data-testid="files-dropzone"
      onDragOver={(event) => { event.preventDefault(); if (!lock.current) setDragging(true); }}
      onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setDragging(false); }}
      onDrop={(event) => { event.preventDefault(); setDragging(false); send(event.dataTransfer.files); }}>
      <input ref={input} type="file" multiple accept={config?.extensions.join(",")} className="sr-only" tabIndex={-1}
        aria-label="Selecionar arquivos" data-testid="files-upload-input" disabled={!config || !!upload}
        onChange={(event) => { send(event.target.files); event.target.value = ""; }} />
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <div className="file-upload-symbol" aria-hidden="true"><UploadCloud size={26} /></div>
        <div className="flex-1 min-w-0">
          <h2 className="font-display text-lg font-semibold" data-testid="files-upload-title">Documentos e mídia</h2>
          <p className="text-sm text-slate-400 mt-1" data-testid="files-upload-limits">PDF, Office, imagens, vídeos e áudios · Até {config ? formatSize(config.max_file_size) : "25 MB"} por arquivo</p>
        </div>
        <button className="btn-primary shrink-0" disabled={!config || !!upload} onClick={() => input.current?.click()} data-testid="files-upload-button">
          {upload ? <LoaderCircle size={17} className="animate-spin" /> : <UploadCloud size={17} />}{upload ? "Enviando…" : "Enviar arquivos"}
        </button>
      </div>
      {upload && <div className="mt-5" role="status" aria-live="polite" data-testid="files-upload-status">
        <p className="text-sm text-blue-200 break-all mb-2" data-testid="files-upload-current">{upload.index}/{upload.total} · {upload.name} · {upload.progress >= 95 ? "Salvando…" : `${upload.progress}%`}</p>
        <Progress value={upload.progress} aria-label="Progresso do envio" className="bg-white/10 [&>div]:bg-blue-400 [&>div]:transition-transform" data-testid="files-upload-progress" />
      </div>}
      {!!errors.length && <ul className="mt-4 space-y-2 text-sm text-red-300 break-words" role="alert" data-testid="files-upload-errors">
        {errors.map((error, index) => <li key={index} data-testid={`files-upload-error-${index}`}>{error}</li>)}
      </ul>}
    </section>
  );
};