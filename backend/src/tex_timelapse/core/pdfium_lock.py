import threading

# PDFium keeps global process-wide state and is NOT thread-safe: concurrent
# use of PdfDocument from several worker threads segfaults (SIGSEGV, exit 139)
# roughly two runs in three on the sample project.
#
# This did not bite while rasterisation went through `pdftoppm`, because every
# call was a separate subprocess and therefore isolated by construction. Moving
# to the in-process pypdfium2 binding removed that isolation, so access has to
# be serialised explicitly.
#
# Every pypdfium2 call - opening a document, rendering, reading page sizes,
# closing - must happen while holding this lock. It is reentrant so nested
# helpers on one thread cannot deadlock.
#
# Cost: page rasterisation is effectively single-threaded. That is a good
# trade, because the pipeline's dominant cost is the LaTeX compile in
# CompileLatexAction, which still runs fully in parallel.
PDFIUM_LOCK = threading.RLock()
