import Link from "next/link"
import { AppSidebar } from "@/components/app-sidebar"
import { PageHeader } from "@/components/page-header"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  FilePlus2Icon,
  BarChart3Icon,
  MapPinIcon,
  ChevronRightIcon,
  FileTextIcon,
} from "lucide-react"

export default function Page() {
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
        <PageHeader title="Dashboard" />
        <div className="flex flex-1 flex-col">
          <div className="@container/main flex flex-1 flex-col gap-2">
            <div className="flex flex-col gap-6 px-4 py-6 md:gap-8 md:px-6 md:py-8">
              {/* Hero + primary CTA */}
              <Card className="overflow-hidden border-primary/20 bg-gradient-to-br from-primary/5 via-card to-card">
                <CardHeader>
                  <CardTitle className="text-xl md:text-2xl">
                    Welcome to DataSite Impact Analyzer
                  </CardTitle>
                  <CardDescription className="max-w-xl text-base">
                    Score proposed data centre sites on environmental, economic,
                    and sociological impact using Canadian open data and
                    AI-powered analysis.
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex flex-wrap gap-2">
                  <Button asChild size="lg">
                    <Link href="/dashboard/new-proposal">
                      <FilePlus2Icon className="mr-2 size-4" />
                      New proposal
                    </Link>
                  </Button>
                  <Button asChild variant="outline" size="lg">
                    <Link href="/dashboard/results">
                      <BarChart3Icon className="mr-2 size-4" />
                      View sample results
                    </Link>
                  </Button>
                </CardContent>
              </Card>

              {/* Quick stats – placeholders for future API */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <Card className="data-[slot=card]:shadow-xs">
                  <CardHeader>
                    <CardDescription>Assessments run</CardDescription>
                    <CardTitle className="text-2xl font-semibold tabular-nums">
                      —
                    </CardTitle>
                    <CardAction>
                      <Badge variant="outline">Placeholder</Badge>
                    </CardAction>
                  </CardHeader>
                  <CardFooter className="flex-col items-start gap-1 text-sm text-muted-foreground">
                    Will show total impact reports
                  </CardFooter>
                </Card>
                <Card className="data-[slot=card]:shadow-xs">
                  <CardHeader>
                    <CardDescription>Proposals this month</CardDescription>
                    <CardTitle className="text-2xl font-semibold tabular-nums">
                      —
                    </CardTitle>
                    <CardAction>
                      <Badge variant="outline">Placeholder</Badge>
                    </CardAction>
                  </CardHeader>
                  <CardFooter className="flex-col items-start gap-1 text-sm text-muted-foreground">
                    Integrate with proposal list
                  </CardFooter>
                </Card>
                <Card className="data-[slot=card]:shadow-xs">
                  <CardHeader>
                    <CardDescription>Avg. overall score</CardDescription>
                    <CardTitle className="text-2xl font-semibold tabular-nums">
                      —
                    </CardTitle>
                    <CardAction>
                      <Badge variant="outline">Placeholder</Badge>
                    </CardAction>
                  </CardHeader>
                  <CardFooter className="flex-col items-start gap-1 text-sm text-muted-foreground">
                    Green / amber / red rollup
                  </CardFooter>
                </Card>
                <Card className="data-[slot=card]:shadow-xs">
                  <CardHeader>
                    <CardDescription>Locations assessed</CardDescription>
                    <CardTitle className="text-2xl font-semibold tabular-nums">
                      —
                    </CardTitle>
                    <CardAction>
                      <Badge variant="outline">Placeholder</Badge>
                    </CardAction>
                  </CardHeader>
                  <CardFooter className="flex-col items-start gap-1 text-sm text-muted-foreground">
                    Unique provinces / regions
                  </CardFooter>
                </Card>
              </div>

              <div>
                {/* Recent proposals – placeholder table */}
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0">
                    <div>
                      <CardTitle>Recent proposals</CardTitle>
                      <CardDescription>
                        Your latest impact assessments (placeholder)
                      </CardDescription>
                    </div>
                    <Button variant="ghost" size="lg" asChild>
                      <Link href="/dashboard/new-proposal">
                        New
                        <ChevronRightIcon className="ml-1 size-4" />
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
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        <TableRow>
                          <TableCell
                            colSpan={4}
                            className="h-32 text-center"
                          >
                            <div className="flex flex-col items-center justify-center gap-2">
                              <FileTextIcon className="size-10 text-muted-foreground/50" />
                              <p className="text-sm font-medium text-muted-foreground">
                                No proposals yet
                              </p>
                              <p className="text-xs text-muted-foreground">
                                Create a proposal to see impact results here
                              </p>
                              <Button asChild size="lg" className="mt-2">
                                <Link href="/dashboard/new-proposal">
                                  Create first proposal
                                </Link>
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
              </div>

              {/* Proposals by province – chart placeholder */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <MapPinIcon className="size-4" />
                    Proposals by province
                  </CardTitle>
                  <CardDescription>
                    Placeholder for future chart or map (e.g. bar chart by
                    province)
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex h-40 items-center justify-center rounded-lg border border-dashed bg-muted/20">
                    <p className="text-sm text-muted-foreground">
                      Chart / map integration coming later
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
