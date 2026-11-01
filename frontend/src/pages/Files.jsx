import { useState } from "react";
import { ArrowLeft, ArrowRight, FolderOpen, LockKeyhole, Search } from "lucide-react";
import { toast } from "sonner";
import { api, errorMessage } from "@/lib/api";
import { FILE_KINDS, downloadFile, fileError, formatSize } from "@/lib/files";
import { PageHeader, Empty } from "@/components/MonthSwitcher";
import { FileUpload } from "@/components/files/FileUpload";
import { FileRow } from "@/components/files/FileRow";
import { FileDeleteDialog, FilePreview } from "@/components/files/FileDialogs";
import { useFileLibrary } from "@/components/files/useFileLibrary";

export default function Files() {
  const library = useFileLibrary();
  const [preview, setPreview] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const [downloading, setDownloading] = useState({});
  const [downloadError, setDownloadError] = useState("");
  const { data, loading, error } = library;

  const download = async (file) => {
    setDownloadError(""); setDownloading((state) => ({ ...state, [file.id]: true }));
    try { await downloadFile(file); }
    catch (e) { setDownloadError(await fileError(e)); }
    finally { setDownloading((state) => ({ ...state, [file.id]: false })); }
  };
  const remove = async () => {
    if (deleteBusy) return;
    setDeleteBusy(true); setDeleteError("");
    try {
      await api.delete(`/files/${deleting.id}`);
      setDeleting(null); library.refresh(); toast.success("Arquivo excluído da biblioteca");
    } catch (e) { setDeleteError(errorMessage(e)); }
    finally { setDeleteBusy(false); }
  };
  const totalPages = Math.max(1, Math.ceil((data?.total || 0) / (data?.page_size || 24)));

  return <div className="files-page">
    <PageHeader eyebrow="Biblioteca privada" title="Seus arquivos">
      <span className="inline-flex items-center gap-2 text-sm text-emerald-300" data-testid="files-privacy-label"><LockKeyhole size={16} />Só você tem acesso</span>
    </PageHeader>
    <FileUpload config={library.config} onUploaded={library.uploaded} />
    <section className="mt-9 rise" aria-label="Biblioteca de arquivos" data-testid="files-library">
      <div className="flex flex-col sm:flex-row gap-3 mb-5">
        <label className="search min-w-0 flex-1"><Search size={17} className="text-slate-400 shrink-0" /><input className="min-w-0" value={library.query} maxLength={180}
          onChange={(e) => library.search(e.target.value)} placeholder="Buscar arquivo pelo nome" aria-label="Buscar arquivo pelo nome" data-testid="files-search-input" /></label>
        <select className="select" value={library.kind} onChange={(e) => library.filter(e.target.value)} aria-label="Tipo de arquivo" data-testid="files-filter-type">
          {Object.entries(FILE_KINDS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select>
      </div>
      {downloadError && <p role="alert" className="text-sm text-red-300 mb-4" data-testid="files-download-error">{downloadError}</p>}
      {error ? <div className="py-12 text-center" role="alert" data-testid="files-load-error">
        <p className="text-red-300 mb-4">{error}</p><button className="btn-ghost" onClick={library.refresh} data-testid="files-retry-button">Tentar novamente</button>
      </div> : loading ? <div className="py-16" role="status" aria-label="Carregando arquivos" data-testid="files-loading"><div className="spinner mx-auto" /></div>
        : <>
          <div className="flex justify-between items-center gap-3 pb-4 border-b border-white/10 text-xs text-slate-400">
            <span data-testid="files-count">{data?.total || 0} {(data?.total || 0) === 1 ? "arquivo" : "arquivos"}</span>
            <span className="tabular" data-testid="files-total-size">{formatSize(data?.total_size)}</span>
          </div>
          {!data?.items.length ? <Empty icon={FolderOpen} text={library.query || library.kind !== "all" ? "Nenhum arquivo encontrado." : "Sua biblioteca ainda está vazia."} testId="files-empty" />
            : <ul data-testid="files-list">{data.items.map((file) => <FileRow key={file.id} file={file} downloading={!!downloading[file.id]} onPreview={(item) => { setDownloadError(""); setPreview(item); }} onDownload={download}
              onDelete={(item) => { setDeleting(item); setDeleteError(""); }} />)}</ul>}
          {totalPages > 1 && <nav className="flex flex-wrap justify-center items-center gap-4 pt-6" aria-label="Páginas de arquivos" data-testid="files-pagination">
            <button className="btn-ghost" disabled={library.page === 1} onClick={() => library.setPage(library.page - 1)} aria-label="Página anterior" data-testid="files-previous-page"><ArrowLeft size={17} /></button>
            <span className="text-sm text-slate-400" data-testid="files-page-number">{library.page} de {totalPages}</span>
            <button className="btn-ghost" disabled={library.page >= totalPages} onClick={() => library.setPage(library.page + 1)} aria-label="Próxima página" data-testid="files-next-page"><ArrowRight size={17} /></button>
          </nav>}
        </>}
    </section>
    <FilePreview key={preview?.id || "closed"} file={preview} onClose={() => setPreview(null)} onDownload={download} downloading={!!downloading[preview?.id]} downloadError={downloadError} />
    <FileDeleteDialog file={deleting} onClose={() => setDeleting(null)} onConfirm={remove} busy={deleteBusy} error={deleteError} />
  </div>;
}