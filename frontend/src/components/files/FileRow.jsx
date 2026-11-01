import { Download, Eye, FileText, Image, Film, Music, Trash2 } from "lucide-react";
import { formatSize } from "@/lib/files";

const ICONS = { document: FileText, image: Image, video: Film, audio: Music };

export const FileRow = ({ file, downloading, onPreview, onDownload, onDelete }) => {
  const Icon = ICONS[file.kind] || FileText;
  const date = new Date(file.created_at).toLocaleDateString("pt-BR");
  return (
    <li className="file-row" data-testid={`file-row-${file.id}`}>
      <span className={`file-type-icon file-type-${file.kind}`} aria-hidden="true"><Icon size={21} /></span>
      <div className="min-w-0 flex-1">
        <button className="text-left font-medium text-sm text-slate-100 hover:text-blue-300 transition-colors break-all" onClick={() => onPreview(file)}
          data-testid={`file-name-${file.id}`}>{file.original_filename}</button>
        <p className="mt-1 text-xs text-slate-400" data-testid={`file-details-${file.id}`}>{formatSize(file.size)} <span className="sm:hidden">· {date}</span></p>
      </div>
      <time className="hidden sm:block text-xs text-slate-400 shrink-0" dateTime={file.created_at} data-testid={`file-date-${file.id}`}>{date}</time>
      <div className="file-row-actions">
        <button className="icon-btn" onClick={() => onPreview(file)} title="Visualizar arquivo" aria-label={`Visualizar ${file.original_filename}`} data-testid={`file-preview-${file.id}`}><Eye size={17} /></button>
        <button className="icon-btn disabled:opacity-40" disabled={downloading} onClick={() => onDownload(file)} title="Baixar arquivo" aria-label={`Baixar ${file.original_filename}`} data-testid={`file-download-${file.id}`}><Download size={17} className={downloading ? "animate-pulse" : ""} /></button>
        <button className="icon-btn hover:!text-red-300" onClick={() => onDelete(file)} title="Excluir arquivo" aria-label={`Excluir ${file.original_filename}`} data-testid={`file-delete-${file.id}`}><Trash2 size={17} /></button>
      </div>
    </li>
  );
};