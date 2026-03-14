"use client"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { UploadIcon, FileTextIcon, PenLineIcon } from "lucide-react"

export function UploadProposalDialog({
  trigger,
}: {
  trigger?: React.ReactNode
}) {
  const [open, setOpen] = useState(false)
  const [pasteText, setPasteText] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [isParsing, setIsParsing] = useState(false)

  const handleParse = () => {
    setIsParsing(true)
    setTimeout(() => {
      setIsParsing(false)
      setOpen(false)
    }, 1500)
  }

  const handleOpenChange = (next: boolean) => {
    if (!next) {
      setPasteText("")
      setFile(null)
    }
    setOpen(next)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        {trigger ?? (
          <Button variant="link" size="lg" className="h-auto p-0 text-sm">
            <UploadIcon className="mr-1.5 size-4" />
            Or upload a PDF to parse into the form
          </Button>
        )}
      </DialogTrigger>
      <DialogContent
        className="sm:max-w-lg"
        showCloseButton={true}
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <UploadIcon className="size-5 text-muted-foreground" />
            Parse proposal from document
          </DialogTitle>
          <DialogDescription>
            Upload a PDF or paste text from a proposal. We’ll extract fields into
            the form for you to confirm. You can also close and enter
            everything manually.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-2">
          <div className="space-y-2">
            <Label>Upload PDF</Label>
            <div
              className="flex min-h-24 flex-col items-center justify-center rounded-lg border border-dashed bg-muted/30 px-4 py-6"
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault()
                const f = e.dataTransfer.files?.[0]
                if (f?.type === "application/pdf") setFile(f)
              }}
            >
              <input
                type="file"
                accept=".pdf,application/pdf"
                className="sr-only"
                id="pdf-upload-dialog"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <label
                htmlFor="pdf-upload-dialog"
                className="cursor-pointer text-center"
              >
                <FileTextIcon className="mx-auto size-8 text-muted-foreground" />
                <p className="mt-1 text-xs font-medium text-muted-foreground">
                  {file ? file.name : "Drop PDF or click to browse"}
                </p>
              </label>
            </div>
          </div>
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase text-muted-foreground">
              Or paste text
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="paste-text-dialog">Pasted proposal text</Label>
            <textarea
              id="paste-text-dialog"
              placeholder="Paste excerpt from a proposal document…"
              className="min-h-20 w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring"
              value={pasteText}
              onChange={(e) => setPasteText(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter showCloseButton={false}>
          <Button
            size="lg"
            onClick={handleParse}
            disabled={isParsing || (!file && !pasteText.trim())}
          >
            {isParsing ? "Parsing…" : "Parse proposal"}
          </Button>
          <Button
            variant="outline"
            size="lg"
            onClick={() => setOpen(false)}
          >
            <PenLineIcon className="mr-2 size-4" />
            Enter manually
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
