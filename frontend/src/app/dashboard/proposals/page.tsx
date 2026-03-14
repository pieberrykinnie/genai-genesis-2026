"use client"

import Link from "next/link"
import { AppSidebar } from "@/components/app-sidebar"
import { PageHeader } from "@/components/page-header"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { FileTextIcon, FilePlus2Icon } from "lucide-react"

export default function ProposalsPage() {
  // UI only: no real data yet. Empty state for now.
  const hasProposals = false

  return (
    <SidebarProvider
      style={
        {
          "--sidebar-width": "calc(var(--spacing) * 72)",
          "--header-height": "calc(var(--spacing) * 12)",
        } as React.CSSProperties
      }
    >
      <AppSidebar variant="inset" />
      <SidebarInset>
        <PageHeader title="Proposals" />
        <div className="flex flex-1 flex-col">
          <div className="@container/main flex flex-1 flex-col gap-2">
            <div className="mx-auto w-full max-w-5xl flex flex-col gap-6 px-4 py-6 md:gap-8 md:px-6 md:py-8">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <FileTextIcon className="size-5" />
                      All proposals
                    </CardTitle>
                    <CardDescription>
                      Past impact assessments. Open one to view the report or run
                      a new assessment.
                    </CardDescription>
                  </div>
                  <Button size="lg" asChild>
                    <Link href="/dashboard/new-proposal">
                      <FilePlus2Icon className="mr-2 size-4" />
                      New proposal
                    </Link>
                  </Button>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name / Location</TableHead>
                        <TableHead>Province</TableHead>
                        <TableHead>Score</TableHead>
                        <TableHead>Date</TableHead>
                        <TableHead className="w-24">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {!hasProposals && (
                        <TableRow>
                          <TableCell
                            colSpan={5}
                            className="h-40 text-center"
                          >
                            <div className="flex flex-col items-center justify-center gap-2">
                              <FileTextIcon className="size-10 text-muted-foreground/50" />
                              <p className="text-sm font-medium text-muted-foreground">
                                No proposals yet
                              </p>
                              <p className="text-xs text-muted-foreground">
                                Create a proposal to see it listed here
                              </p>
                              <Button asChild size="lg" className="mt-2">
                                <Link href="/dashboard/new-proposal">
                                  Create first proposal
                                </Link>
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
