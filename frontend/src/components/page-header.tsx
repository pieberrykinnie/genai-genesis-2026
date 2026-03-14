import { Separator } from "@/components/ui/separator"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { cn } from "@/lib/utils"

const defaultHeaderClass =
  "flex h-(--header-height) shrink-0 items-center gap-2 border-b transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-(--header-height)"

export interface PageHeaderProps {
  /** Title shown in the header */
  title: string
  /** Optional additional content (e.g. actions) to render after the title */
  children?: React.ReactNode
  /** Optional className for the header element (merged with default) */
  className?: string
}

export function PageHeader({ title, children, className }: PageHeaderProps) {
  return (
    <header className={cn(defaultHeaderClass, className)}>
      <div className="flex w-full items-center gap-1 px-4 lg:gap-2 lg:px-6">
        <SidebarTrigger className="-ml-1" />
        <Separator
          orientation="vertical"
          className="mx-2 data-[orientation=vertical]:h-4"
        />
        <h1 className="text-base font-medium">{title}</h1>
        {children}
      </div>
    </header>
  )
}
