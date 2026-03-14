"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { AppSidebar } from "@/components/app-sidebar"
import { PageHeader } from "@/components/page-header"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import type {
  DataCentreProposal,
  CanadianProvince,
  CoolingType,
  FacilityType,
} from "@/types/assessment"
import { UploadProposalDialog } from "@/components/upload-proposal-dialog"
import {
  Building2Icon,
  MapPinIcon,
  SettingsIcon,
  DollarSignIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  PlayIcon,
} from "lucide-react"

const PROPOSAL_STEPS = [
  { id: "basic-info", label: "Basic Info", icon: Building2Icon },
  { id: "location", label: "Location", icon: MapPinIcon },
  { id: "specification", label: "Specification", icon: SettingsIcon },
  { id: "economics", label: "Economics", icon: DollarSignIcon },
] as const

type StepId = (typeof PROPOSAL_STEPS)[number]["id"]

const PROVINCES: { value: CanadianProvince; label: string }[] = [
  { value: "ON", label: "Ontario" },
  { value: "AB", label: "Alberta" },
  { value: "BC", label: "British Columbia" },
  { value: "QC", label: "Quebec" },
  { value: "MB", label: "Manitoba" },
  { value: "SK", label: "Saskatchewan" },
  { value: "NS", label: "Nova Scotia" },
  { value: "NB", label: "New Brunswick" },
  { value: "NL", label: "Newfoundland and Labrador" },
  { value: "PE", label: "Prince Edward Island" },
]

const COOLING_TYPES: { value: CoolingType; label: string }[] = [
  { value: "air", label: "Air" },
  { value: "evaporative", label: "Evaporative" },
  { value: "liquid_immersion", label: "Liquid immersion" },
  { value: "hybrid", label: "Hybrid" },
]

const FACILITY_TYPES: { value: FacilityType; label: string }[] = [
  { value: "hyperscale", label: "Hyperscale" },
  { value: "enterprise", label: "Enterprise" },
  { value: "colocation", label: "Colocation" },
]

const defaultProposal: DataCentreProposal = {
  address: "",
  province: "ON",
  it_load_mw: 50,
  pue: 1.5,
  wue: 1.9,
  cooling_type: "evaporative",
  facility_type: "hyperscale",
  capex_cad: 200,
  construction_months: 24,
  has_onsite_generation: false,
  renewable_ppa: false,
}

export default function NewProposalPage() {
  const router = useRouter()
  const [activeStepId, setActiveStepId] = useState<StepId>(PROPOSAL_STEPS[0].id)
  const [form, setForm] = useState<DataCentreProposal>(defaultProposal)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const currentIndex = PROPOSAL_STEPS.findIndex((s) => s.id === activeStepId)
  const canGoPrev = currentIndex > 0
  const canGoNext = currentIndex < PROPOSAL_STEPS.length - 1
  const isLastStep = currentIndex === PROPOSAL_STEPS.length - 1
  const stepNumber = currentIndex + 1

  const update = <K extends keyof DataCentreProposal>(
    key: K,
    value: DataCentreProposal[K]
  ) => setForm((prev) => ({ ...prev, [key]: value }))

  const handleRunAnalysis = async () => {
    setIsSubmitting(true)
    try {
      router.push("/dashboard/results")
    } finally {
      setIsSubmitting(false)
    }
  }

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
        <PageHeader title="New proposal" />
        <div className="flex flex-1 flex-col">
          <div className="@container/main flex flex-1 flex-col gap-2">
            <div className="mx-auto w-full max-w-5xl flex flex-col gap-6 px-4 py-6 md:gap-8 md:px-6 md:py-8">
              {/* Intro */}
              <Card className="border-primary/20 bg-gradient-to-br from-primary/5 via-card to-card">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">
                    Create a data centre impact assessment
                  </CardTitle>
                  <CardDescription>
                    Complete each step with the proposal details. Your inputs
                    are used with Canadian open data and AI to produce
                    environmental, economic, and sociological scores.
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-0">
                  <UploadProposalDialog />
                </CardContent>
              </Card>

              <Tabs
                value={activeStepId}
                onValueChange={(v) => setActiveStepId(v as StepId)}
                className="w-full"
              >
                <TabsList variant="line" className="mb-1 w-full md:flex">
                  {PROPOSAL_STEPS.map((step, i) => {
                    const Icon = step.icon
                    return (
                      <TabsTrigger
                        key={step.id}
                        value={step.id}
                        className="flex flex-1 items-center gap-2"
                      >
                        <Icon className="size-4 shrink-0" />
                        <span className="hidden sm:inline">{step.label}</span>
                        <Badge
                          variant="secondary"
                          className="ml-1 size-5 shrink-0 rounded-full p-0 text-xs font-normal"
                        >
                          {i + 1}
                        </Badge>
                      </TabsTrigger>
                    )
                  })}
                </TabsList>

                {/* Basic Info */}
                <TabsContent value="basic-info" className="mt-0">
                  <Card>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <div>
                          <CardTitle className="flex items-center gap-2">
                            <Building2Icon className="size-5 text-muted-foreground" />
                            Basic Info
                          </CardTitle>
                          <CardDescription className="mt-1">
                            Facility type and key technical parameters used for
                            impact calculations
                          </CardDescription>
                        </div>
                        <Badge variant="outline">
                          Step {stepNumber} of {PROPOSAL_STEPS.length}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div className="space-y-4">
                        <p className="text-sm font-medium text-muted-foreground">
                          Facility & scale
                        </p>
                        <div className="grid gap-4 sm:grid-cols-2">
                          <div className="space-y-2">
                            <Label htmlFor="facility_type">Facility type</Label>
                            <Select
                              value={form.facility_type}
                              onValueChange={(v) =>
                                update("facility_type", v as FacilityType)
                              }
                            >
                              <SelectTrigger id="facility_type" className="w-full">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {FACILITY_TYPES.map((o) => (
                                  <SelectItem key={o.value} value={o.value}>
                                    {o.label}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="space-y-2">
                            <Label htmlFor="it_load_mw">IT load (MW)</Label>
                            <Input
                              id="it_load_mw"
                              type="number"
                              min={1}
                              max={500}
                              value={form.it_load_mw}
                              onChange={(e) =>
                                update("it_load_mw", Number(e.target.value) || 0)
                              }
                              className="w-full"
                            />
                            <p className="text-xs text-muted-foreground">
                              Typical range 1–500 MW
                            </p>
                          </div>
                        </div>
                      </div>

                      <Separator />

                      <div className="space-y-4">
                        <p className="text-sm font-medium text-muted-foreground">
                          Efficiency & cooling
                        </p>
                        <div className="grid gap-4 sm:grid-cols-2">
                          <div className="space-y-2">
                            <Label htmlFor="pue">PUE</Label>
                            <Input
                              id="pue"
                              type="number"
                              min={1.1}
                              max={2}
                              step={0.1}
                              value={form.pue}
                              onChange={(e) =>
                                update("pue", Number(e.target.value) || 1.5)
                              }
                              className="w-full"
                            />
                            <p className="text-xs text-muted-foreground">
                              Power usage effectiveness (1.1–2.0, typical ~1.5)
                            </p>
                          </div>
                          <div className="space-y-2">
                            <Label htmlFor="wue">WUE (L/kWh)</Label>
                            <Input
                              id="wue"
                              type="number"
                              min={0.5}
                              max={3}
                              step={0.1}
                              value={form.wue}
                              onChange={(e) =>
                                update("wue", Number(e.target.value) || 1.9)
                              }
                              className="w-full"
                            />
                            <p className="text-xs text-muted-foreground">
                              Water usage effectiveness
                            </p>
                          </div>
                          <div className="space-y-2 sm:col-span-2">
                            <Label htmlFor="cooling_type">Cooling type</Label>
                            <Select
                              value={form.cooling_type}
                              onValueChange={(v) =>
                                update("cooling_type", v as CoolingType)
                              }
                            >
                              <SelectTrigger id="cooling_type" className="w-full">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {COOLING_TYPES.map((o) => (
                                  <SelectItem key={o.value} value={o.value}>
                                    {o.label}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                    <CardFooter className="flex gap-2 border-t pt-6">
                      <Button
                        variant="outline"
                        size="lg"
                        onClick={() =>
                          setActiveStepId(PROPOSAL_STEPS[currentIndex - 1].id)
                        }
                        disabled={!canGoPrev}
                      >
                        <ChevronLeftIcon className="mr-1 size-4" />
                        Previous
                      </Button>
                      <Button
                        size="lg"
                        onClick={() =>
                          setActiveStepId(PROPOSAL_STEPS[currentIndex + 1].id)
                        }
                        disabled={!canGoNext}
                      >
                        Next
                        <ChevronRightIcon className="ml-1 size-4" />
                      </Button>
                    </CardFooter>
                  </Card>
                </TabsContent>

                {/* Location */}
                <TabsContent value="location" className="mt-0">
                  <Card>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <div>
                          <CardTitle className="flex items-center gap-2">
                            <MapPinIcon className="size-5 text-muted-foreground" />
                            Location
                          </CardTitle>
                          <CardDescription className="mt-1">
                            Canadian address and province for grid, census, and
                            water data lookups
                          </CardDescription>
                        </div>
                        <Badge variant="outline">
                          Step {stepNumber} of {PROPOSAL_STEPS.length}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div className="grid gap-4 sm:grid-cols-2">
                        <div className="space-y-2 sm:col-span-2">
                          <Label htmlFor="address">Address</Label>
                          <Input
                            id="address"
                            value={form.address}
                            onChange={(e) => update("address", e.target.value)}
                            placeholder="e.g. 123 Main St, City"
                            className="w-full"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="province">Province</Label>
                          <Select
                            value={form.province}
                            onValueChange={(v) =>
                              update("province", v as CanadianProvince)
                            }
                          >
                            <SelectTrigger id="province" className="w-full">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {PROVINCES.map((p) => (
                                <SelectItem key={p.value} value={p.value}>
                                  {p.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="flex items-end">
                          <Button variant="outline" size="lg" asChild>
                            <Link href="/dashboard/new-proposal/map">
                              <MapPinIcon className="mr-2 size-4" />
                              Pick on map
                            </Link>
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                    <CardFooter className="flex gap-2 border-t pt-6">
                      <Button
                        variant="outline"
                        size="lg"
                        onClick={() =>
                          setActiveStepId(PROPOSAL_STEPS[currentIndex - 1].id)
                        }
                        disabled={!canGoPrev}
                      >
                        <ChevronLeftIcon className="mr-1 size-4" />
                        Previous
                      </Button>
                      <Button
                        size="lg"
                        onClick={() =>
                          setActiveStepId(PROPOSAL_STEPS[currentIndex + 1].id)
                        }
                        disabled={!canGoNext}
                      >
                        Next
                        <ChevronRightIcon className="ml-1 size-4" />
                      </Button>
                    </CardFooter>
                  </Card>
                </TabsContent>

                {/* Specification */}
                <TabsContent value="specification" className="mt-0">
                  <Card>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <div>
                          <CardTitle className="flex items-center gap-2">
                            <SettingsIcon className="size-5 text-muted-foreground" />
                            Specification
                          </CardTitle>
                          <CardDescription className="mt-1">
                            Core parameters are in Basic Info. Additional
                            technical fields can be added here when needed.
                          </CardDescription>
                        </div>
                        <Badge variant="outline">
                          Step {stepNumber} of {PROPOSAL_STEPS.length}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="rounded-lg border border-dashed bg-muted/30 p-6 text-center">
                        <SettingsIcon className="mx-auto size-10 text-muted-foreground/50" />
                        <p className="mt-2 text-sm text-muted-foreground">
                          No extra specification fields yet
                        </p>
                      </div>
                    </CardContent>
                    <CardFooter className="flex gap-2 border-t pt-6">
                      <Button
                        variant="outline"
                        size="lg"
                        onClick={() =>
                          setActiveStepId(PROPOSAL_STEPS[currentIndex - 1].id)
                        }
                        disabled={!canGoPrev}
                      >
                        <ChevronLeftIcon className="mr-1 size-4" />
                        Previous
                      </Button>
                      <Button
                        size="lg"
                        onClick={() =>
                          setActiveStepId(PROPOSAL_STEPS[currentIndex + 1].id)
                        }
                        disabled={!canGoNext}
                      >
                        Next
                        <ChevronRightIcon className="ml-1 size-4" />
                      </Button>
                    </CardFooter>
                  </Card>
                </TabsContent>

                {/* Economics */}
                <TabsContent value="economics" className="mt-0">
                  <Card>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <div>
                          <CardTitle className="flex items-center gap-2">
                            <DollarSignIcon className="size-5 text-muted-foreground" />
                            Economics
                          </CardTitle>
                          <CardDescription className="mt-1">
                            Investment and sustainability options that affect
                            the impact report
                          </CardDescription>
                        </div>
                        <Badge variant="outline">
                          Step {stepNumber} of {PROPOSAL_STEPS.length}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      <div className="space-y-4">
                        <p className="text-sm font-medium text-muted-foreground">
                          Investment
                        </p>
                        <div className="grid gap-4 sm:grid-cols-2">
                          <div className="space-y-2">
                            <Label htmlFor="capex_cad">CapEx (CAD millions)</Label>
                            <Input
                              id="capex_cad"
                              type="number"
                              min={0}
                              value={form.capex_cad}
                              onChange={(e) =>
                                update("capex_cad", Number(e.target.value) || 0)
                              }
                              className="w-full"
                            />
                          </div>
                          <div className="space-y-2">
                            <Label htmlFor="construction_months">
                              Construction (months)
                            </Label>
                            <Input
                              id="construction_months"
                              type="number"
                              min={12}
                              max={48}
                              value={form.construction_months}
                              onChange={(e) =>
                                update(
                                  "construction_months",
                                  Number(e.target.value) || 12
                                )
                              }
                              className="w-full"
                            />
                            <p className="text-xs text-muted-foreground">
                              12–48 months
                            </p>
                          </div>
                        </div>
                      </div>

                      <Separator />

                      <div className="space-y-4">
                        <p className="text-sm font-medium text-muted-foreground">
                          Sustainability options
                        </p>
                        <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap">
                          <div className="flex items-center space-x-2 rounded-lg border bg-muted/30 px-4 py-3">
                            <Checkbox
                              id="has_onsite_generation"
                              checked={form.has_onsite_generation ?? false}
                              onCheckedChange={(checked) =>
                                update("has_onsite_generation", !!checked)
                              }
                            />
                            <Label
                              htmlFor="has_onsite_generation"
                              className="cursor-pointer font-normal"
                            >
                              Has onsite generation
                            </Label>
                          </div>
                          <div className="flex items-center space-x-2 rounded-lg border bg-muted/30 px-4 py-3">
                            <Checkbox
                              id="renewable_ppa"
                              checked={form.renewable_ppa ?? false}
                              onCheckedChange={(checked) =>
                                update("renewable_ppa", !!checked)
                              }
                            />
                            <Label
                              htmlFor="renewable_ppa"
                              className="cursor-pointer font-normal"
                            >
                              Renewable PPA
                            </Label>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                    <CardFooter className="flex gap-2 border-t pt-6">
                      <Button
                        variant="outline"
                        size="lg"
                        onClick={() =>
                          setActiveStepId(PROPOSAL_STEPS[currentIndex - 1].id)
                        }
                        disabled={!canGoPrev}
                      >
                        <ChevronLeftIcon className="mr-1 size-4" />
                        Previous
                      </Button>
                      {isLastStep ? (
                        <Button
                          size="lg"
                          onClick={handleRunAnalysis}
                          disabled={isSubmitting}
                        >
                          {isSubmitting ? (
                            "Running…"
                          ) : (
                            <>
                              <PlayIcon className="mr-2 size-4" />
                              Run Impact Analysis
                            </>
                          )}
                        </Button>
                      ) : (
                        <Button
                          size="lg"
                          onClick={() =>
                            setActiveStepId(PROPOSAL_STEPS[currentIndex + 1].id)
                          }
                        >
                          Next
                          <ChevronRightIcon className="ml-1 size-4" />
                        </Button>
                      )}
                    </CardFooter>
                  </Card>
                </TabsContent>
              </Tabs>
            </div>
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
