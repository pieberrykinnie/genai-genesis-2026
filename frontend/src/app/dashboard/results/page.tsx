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
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"
import type { ImpactAssessment, RagScore } from "@/types/assessment"
import {
  LeafIcon,
  Building2Icon,
  UsersIcon,
  ZapIcon,
  FileTextIcon,
  ListChecksIcon,
  PlusCircleIcon,
  LayoutDashboardIcon,
} from "lucide-react"

const RAG_STYLES: Record<RagScore, string> = {
  green:
    "border-emerald-500/50 bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  amber:
    "border-amber-500/50 bg-amber-500/15 text-amber-700 dark:text-amber-300",
  red: "border-red-500/50 bg-red-500/15 text-red-700 dark:text-red-300",
}

const RAG_LABELS: Record<RagScore, string> = {
  green: "Green",
  amber: "Amber",
  red: "Red",
}

// Mock result for demo until backend is connected
const mockAssessment: ImpactAssessment = {
  metadata: {
    proposal_id: "demo-1",
    location: "Sample location",
    timestamp: new Date().toISOString(),
    data_freshness: "2024",
  },
  environmental: {
    score: "amber",
    summary:
      "Carbon intensity and water use are within provincial norms; evaporative cooling increases local water demand.",
  },
  economic: {
    score: "green",
    summary:
      "Strong capex and job creation; construction timeline is realistic for the region.",
  },
  sociological: {
    score: "amber",
    summary:
      "Census and Indigenous Services data show moderate sensitivity; community engagement recommended.",
  },
  grid_strain: {
    score: "red",
    probability: 0.72,
    summary:
      "ML model indicates high probability of grid strain given proposed IT load and regional demand.",
  },
  overall_score: "amber",
  negotiation_playbook: [
    "Request binding commitment to renewable PPA or onsite generation before approval.",
    "Tie permit to phased load ramp and grid upgrade milestones.",
    "Require water stewardship plan and WUE targets with annual reporting.",
    "Include community benefit agreement and local hiring targets in conditions.",
  ],
  report_narrative: `This proposed data centre site presents a mixed impact profile. Environmental scores are amber due to water use intensity from evaporative cooling; carbon intensity is acceptable for the provincial grid. Economic indicators are strong. Sociological factors are moderate, with some sensitivity around Indigenous and community considerations. The grid strain model flags a high probability of stress on local infrastructure—this should be addressed in negotiations with the utility and the proponent. Overall, the project is workable with conditions focused on renewables, water, and grid coordination.`,
}

function PillarCard({
  title,
  score,
  summary,
  icon: Icon,
}: {
  title: string
  score: RagScore
  summary?: string
  icon: React.ElementType
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base flex items-center gap-2 font-medium">
          <Icon className="size-4 text-muted-foreground" />
          {title}
        </CardTitle>
        <Badge variant="outline" className={cn("shrink-0", RAG_STYLES[score])}>
          {RAG_LABELS[score]}
        </Badge>
      </CardHeader>
      {summary && (
        <CardContent>
          <p className="text-sm text-muted-foreground leading-relaxed">
            {summary}
          </p>
        </CardContent>
      )}
    </Card>
  )
}

export default function ResultsPage() {
  const data = mockAssessment
  const meta = data.metadata

  const scoreRows: { pillar: string; score: RagScore; summary: string }[] = [
    {
      pillar: "Environmental",
      score: data.environmental.score,
      summary: data.environmental.summary ?? "",
    },
    {
      pillar: "Economic",
      score: data.economic.score,
      summary: data.economic.summary ?? "",
    },
    {
      pillar: "Sociological",
      score: data.sociological.score,
      summary: data.sociological.summary ?? "",
    },
    {
      pillar: "Grid strain",
      score: data.grid_strain.score,
      summary: data.grid_strain.summary ?? "",
    },
  ]

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
        <PageHeader title="Impact report" />
        <div className="flex flex-1 flex-col">
          <div className="@container/main flex flex-1 flex-col gap-2">
            <div className="mx-auto w-full max-w-5xl flex flex-col gap-6 px-4 py-6 md:gap-8 md:px-6 md:py-8">
              {/* Metadata table */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <LayoutDashboardIcon className="size-4" />
                    Report summary
                  </CardTitle>
                  <CardDescription>
                    Proposal and assessment metadata
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[180px]">Field</TableHead>
                        <TableHead>Value</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {meta?.proposal_id && (
                        <TableRow>
                          <TableCell className="font-medium text-muted-foreground">
                            Proposal ID
                          </TableCell>
                          <TableCell>{meta.proposal_id}</TableCell>
                        </TableRow>
                      )}
                      {meta?.location && (
                        <TableRow>
                          <TableCell className="font-medium text-muted-foreground">
                            Location
                          </TableCell>
                          <TableCell>{meta.location}</TableCell>
                        </TableRow>
                      )}
                      {meta?.timestamp && (
                        <TableRow>
                          <TableCell className="font-medium text-muted-foreground">
                            Date
                          </TableCell>
                          <TableCell>
                            {new Date(meta.timestamp).toLocaleString()}
                          </TableCell>
                        </TableRow>
                      )}
                      {meta?.data_freshness && (
                        <TableRow>
                          <TableCell className="font-medium text-muted-foreground">
                            Data freshness
                          </TableCell>
                          <TableCell>{meta.data_freshness}</TableCell>
                        </TableRow>
                      )}
                      <TableRow>
                        <TableCell className="font-medium text-muted-foreground">
                          Overall score
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant="outline"
                            className={cn(RAG_STYLES[data.overall_score])}
                          >
                            {RAG_LABELS[data.overall_score]}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>

              <Separator />

              {/* Score summary table */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Score summary</CardTitle>
                  <CardDescription>
                    Impact scores across pillars and grid strain
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Pillar</TableHead>
                        <TableHead className="w-[100px]">Score</TableHead>
                        <TableHead className="max-w-md">Summary</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {scoreRows.map((row) => (
                        <TableRow key={row.pillar}>
                          <TableCell className="font-medium">
                            {row.pillar}
                          </TableCell>
                          <TableCell>
                            <Badge
                              variant="outline"
                              className={cn(RAG_STYLES[row.score])}
                            >
                              {RAG_LABELS[row.score]}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-muted-foreground text-sm max-w-md whitespace-normal">
                            {row.summary}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>

              {/* Three pillar cards – visual highlight */}
              <div className="grid gap-4 sm:grid-cols-3">
                <PillarCard
                  title="Environmental"
                  score={data.environmental.score}
                  summary={data.environmental.summary}
                  icon={LeafIcon}
                />
                <PillarCard
                  title="Economic"
                  score={data.economic.score}
                  summary={data.economic.summary}
                  icon={Building2Icon}
                />
                <PillarCard
                  title="Sociological"
                  score={data.sociological.score}
                  summary={data.sociological.summary}
                  icon={UsersIcon}
                />
              </div>

              {/* Grid strain */}
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-base flex items-center gap-2 font-medium">
                    <ZapIcon className="size-4 text-muted-foreground" />
                    Grid strain
                  </CardTitle>
                  <Badge
                    variant="outline"
                    className={cn(RAG_STYLES[data.grid_strain.score])}
                  >
                    {RAG_LABELS[data.grid_strain.score]}
                  </Badge>
                </CardHeader>
                <CardContent className="space-y-1">
                  {data.grid_strain.probability != null && (
                    <p className="text-sm text-muted-foreground">
                      Strain probability:{" "}
                      <span className="font-medium text-foreground">
                        {(data.grid_strain.probability * 100).toFixed(0)}%
                      </span>
                    </p>
                  )}
                  {data.grid_strain.summary && (
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      {data.grid_strain.summary}
                    </p>
                  )}
                </CardContent>
              </Card>

              {/* Promises vs calculated reality */}
              <div className="grid gap-4 md:grid-cols-2">
                <Card className="border-emerald-200 bg-emerald-500/5 dark:border-emerald-900/50 dark:bg-emerald-950/20">
                  <CardHeader>
                    <CardTitle className="text-base">
                      Company promises
                    </CardTitle>
                    <CardDescription>
                      Claims made by the proponent (e.g. green power, jobs,
                      water efficiency). Shown for comparison only.
                    </CardDescription>
                  </CardHeader>
                </Card>
                <Card className="ring-2 ring-foreground/10">
                  <CardHeader>
                    <CardTitle className="text-base">
                      Calculated reality
                    </CardTitle>
                    <CardDescription>
                      Scores and narrative above are based on real Canadian open
                      data, IEA/The Green Grid formulas, and the trained grid
                      strain model—no invented figures.
                    </CardDescription>
                  </CardHeader>
                </Card>
              </div>

              <Separator />

              {/* Report narrative */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <FileTextIcon className="size-4" />
                    Full report
                  </CardTitle>
                  <CardDescription>
                    LLM-generated narrative grounded in calculation outputs
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="max-h-52 overflow-y-auto rounded-md border bg-muted/30 p-4 text-sm text-foreground leading-relaxed">
                    {data.report_narrative}
                  </div>
                </CardContent>
              </Card>

              {/* Negotiation playbook – table */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <ListChecksIcon className="size-4" />
                    Negotiation playbook
                  </CardTitle>
                  <CardDescription>
                    Suggested conditions and talking points for council and
                    planners
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-12">#</TableHead>
                        <TableHead>Recommendation</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.negotiation_playbook.map((item, i) => (
                        <TableRow key={i}>
                          <TableCell className="text-muted-foreground font-medium">
                            {i + 1}
                          </TableCell>
                          <TableCell className="text-sm leading-relaxed whitespace-normal">
                            {item}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>

              <Separator />

              {/* Actions */}
              <div className="flex flex-wrap items-center gap-2">
                <Button asChild size="lg">
                  <Link href="/dashboard/new-proposal">
                    <PlusCircleIcon className="mr-2 size-4" />
                    New proposal
                  </Link>
                </Button>
                <Button variant="outline" size="lg" asChild>
                  <Link href="/dashboard">Back to dashboard</Link>
                </Button>
              </div>
            </div>
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
