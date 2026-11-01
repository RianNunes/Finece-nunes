import { useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { getDocument } from "pdfjs-dist/webpack.mjs";

export const PdfPreview = ({ blob }) => {
  const container = useRef(null);
  const canvas = useRef(null);
  const [width, setWidth] = useState(0);
  const [document, setDocument] = useState(null);
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  const [text, setText] = useState("");

  useEffect(() => {
    const observer = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)));
    if (container.current) observer.observe(container.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    let task;
    let closed = false;
    setError(""); setDocument(null); setPage(1); setBusy(true);
    blob.arrayBuffer().then((bytes) => {
      if (closed) return;
      task = getDocument({ data: new Uint8Array(bytes), isEvalSupported: false, useSystemFonts: true, useWasm: false });
      // Password-protected documents retain download access without prompting here.
      return task.promise;
    }).then((pdf) => { if (!closed && pdf) setDocument(pdf); }).catch((e) => {
      if (!closed) {
        setError(e.name === "PasswordException" ? "Este PDF está protegido por senha. Baixe o arquivo para abri-lo." : "Não foi possível visualizar este PDF. O arquivo ainda pode ser baixado.");
        setBusy(false);
      }
    });
    return () => { closed = true; task?.destroy(); };
  }, [blob]);

  useEffect(() => {
    if (!document || !width) return;
    let closed = false;
    let render;
    setBusy(true); setError(""); setText("");
    document.getPage(page).then(async (pdfPage) => {
      if (closed || !canvas.current) return;
      const base = pdfPage.getViewport({ scale: 1 });
      const scale = Math.min(2, window.devicePixelRatio || 1);
      const viewport = pdfPage.getViewport({ scale: (width / base.width) * scale });
      canvas.current.width = Math.floor(viewport.width);
      canvas.current.height = Math.floor(viewport.height);
      render = pdfPage.render({ canvas: canvas.current, canvasContext: canvas.current.getContext("2d"), viewport });
      await render.promise;
      if (!closed) setBusy(false);
      const content = await pdfPage.getTextContent();
      if (!closed) setText(content.items.map((item) => item.str || "").join(" "));
    }).catch((e) => {
      if (!closed && e.name !== "RenderingCancelledException") {
        setError("Não foi possível renderizar esta página. Baixe o PDF para ver o conteúdo completo.");
        setBusy(false);
      }
    });
    return () => { closed = true; render?.cancel(); };
  }, [document, page, width]);

  return <div className="p-3" data-testid="file-preview-pdf">
    {document && <nav className="flex items-center justify-center gap-4 pb-3" aria-label="Páginas do PDF" data-testid="file-pdf-pagination">
      <button className="icon-btn disabled:opacity-30" disabled={page <= 1} onClick={() => setPage(page - 1)} aria-label="Página anterior do PDF" title="Página anterior" data-testid="file-pdf-previous"><ChevronLeft size={20} /></button>
      <span className="text-xs text-slate-300 tabular" data-testid="file-pdf-page">{page} / {document.numPages}</span>
      <button className="icon-btn disabled:opacity-30" disabled={page >= document.numPages} onClick={() => setPage(page + 1)} aria-label="Próxima página do PDF" title="Próxima página" data-testid="file-pdf-next"><ChevronRight size={20} /></button>
    </nav>}
    {error && <p role="alert" className="text-sm text-amber-200 p-4" data-testid="file-pdf-error">{error}</p>}
    {busy && <p role="status" className="text-sm text-blue-200 p-4 text-center" data-testid="file-pdf-loading">Carregando PDF…</p>}
    <div ref={container} className="w-full min-w-0">
      <canvas ref={canvas} className={`w-full h-auto ${busy || error ? "hidden" : "block"}`} role="img" aria-label={`Página ${page} do PDF`} data-testid="file-pdf-canvas" />
      <p className="sr-only" data-testid="file-pdf-text">{text}</p>
    </div>
  </div>;
};

export default PdfPreview;