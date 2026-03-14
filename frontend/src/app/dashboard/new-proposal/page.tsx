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
import type {
  DataCentreProposal,
  CanadianProvince,
  CoolingType,
  FacilityType,
} from "@/types/assessment"

const PROPOSAL_STEPS = [
  { id: "basic-info", label: "Basic Info" },
  { id: "location", label: "Location" },
  { id: "specification", label: "Specification" },
  { id: "economics", label: "Economics" },
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

  const update = <K extends keyof DataCentreProposal>(
    key: K,
    value: DataCentreProposal[K]
  ) => setForm((prev) => ({ ...prev, [key]: value }))

  const handleRunAnalysis = async () => {
    setIsSubmitting(true)
    try {
      // TODO: POST /api/assess or /api/assess/stream when backend is ready
      // For now navigate to results with proposal in state (results page uses mock data)
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
            <div className="flex flex-col gap-6 px-4 py-6 md:gap-8 md:px-6 md:py-8">
              <Tabs
                value={activeStepId}
                onValueChange={(v) => setActiveStepId(v as StepId)}
                className="w-full"
              >
                <TabsList variant="line" className="w-full md:flex">
                  {PROPOSAL_STEPS.map((step) => (
                    <TabsTrigger
                      key={step.id}
                      value={step.id}
                      className="flex-1"
                    >
                      {step.label}
                    </TabsTrigger>
                  ))}
                </TabsList>

                <TabsContent
                  value="basic-info"
                  className="mt-4 rounded-lg border bg-card p-4 md:p-6"
                >
                  <h2 className="text-lg font-semibold text-foreground md:text-xl">
                    Basic Info
                  </h2>
                  <div className="mt-4 grid gap-4 sm:grid-cols-2">
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
                      />
                    </div>
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
                      />
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
                      />
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
                  <div className="mt-6 flex gap-2">
                    <Button
                      variant="outline"
                      size="lg"
                      onClick={() =>
                        setActiveStepId(PROPOSAL_STEPS[currentIndex - 1].id)
                      }
                      disabled={!canGoPrev}
                    >
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
                    </Button>
                  </div>
                </TabsContent>

                <TabsContent
                  value="location"
                  className="mt-4 rounded-lg border bg-card p-4 md:p-6"
                >
                  <h2 className="text-lg font-semibold text-foreground md:text-xl">
                    Location
                  </h2>
                  <div className="mt-4 grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2 sm:col-span-2">
                      <Label htmlFor="address">Address</Label>
                      <Input
                        id="address"
                        value={form.address}
                        onChange={(e) => update("address", e.target.value)}
                        placeholder="e.g. 123 Main St, City"
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
                          Pick on map
                        </Link>
                      </Button>
                    </div>
                  </div>
                  <div className="mt-6 flex gap-2">
                    <Button
                      variant="outline"
                      size="lg"
                      onClick={() =>
                        setActiveStepId(PROPOSAL_STEPS[currentIndex - 1].id)
                      }
                      disabled={!canGoPrev}
                    >
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
                    </Button>
                  </div>
                </TabsContent>

                <TabsContent
                  value="specification"
                  className="mt-4 rounded-lg border bg-card p-4 md:p-6"
                >
                  <h2 className="text-lg font-semibold text-foreground md:text-xl">
                    Specification
                  </h2>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Core technical parameters are in Basic Info. Additional
                    specification fields can be added here when needed.
                  </p>
                  <div className="mt-6 flex gap-2">
                    <Button
                      variant="outline"
                      size="lg"
                      onClick={() =>
                        setActiveStepId(PROPOSAL_STEPS[currentIndex - 1].id)
                      }
                      disabled={!canGoPrev}
                    >
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
                    </Button>
                  </div>
                </TabsContent>

                <TabsContent
                  value="economics"
                  className="mt-4 rounded-lg border bg-card p-4 md:p-6"
                >
                  <h2 className="text-lg font-semibold text-foreground md:text-xl">
                    Economics
                  </h2>
                  <div className="mt-4 grid gap-4 sm:grid-cols-2">
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
                      />
                    </div>
                    <div className="flex items-center space-x-2 sm:col-span-2">
                      <Checkbox
                        id="has_onsite_generation"
                        checked={form.has_onsite_generation ?? false}
                        onCheckedChange={(checked) =>
                          update("has_onsite_generation", !!checked)
                        }
                      />
                      <Label
                        htmlFor="has_onsite_generation"
                        className="font-normal"
                      >
                        Has onsite generation
                      </Label>
                    </div>
                    <div className="flex items-center space-x-2 sm:col-span-2">
                      <Checkbox
                        id="renewable_ppa"
                        checked={form.renewable_ppa ?? false}
                        onCheckedChange={(checked) =>
                          update("renewable_ppa", !!checked)
                        }
                      />
                      <Label htmlFor="renewable_ppa" className="font-normal">
                        Renewable PPA
                      </Label>
                    </div>
                  </div>
                  <div className="mt-6 flex gap-2">
                    <Button
                      variant="outline"
                      size="lg"
                      onClick={() =>
                        setActiveStepId(PROPOSAL_STEPS[currentIndex - 1].id)
                      }
                      disabled={!canGoPrev}
                    >
                      Previous
                    </Button>
                    {isLastStep ? (
                      <Button
                        size="lg"
                        onClick={handleRunAnalysis}
                        disabled={isSubmitting}
                      >
                        {isSubmitting ? "Running…" : "Run Impact Analysis"}
                      </Button>
                    ) : (
                      <Button
                        size="lg"
                        onClick={() =>
                          setActiveStepId(PROPOSAL_STEPS[currentIndex + 1].id)
                        }
                      >
                        Next
                      </Button>
                    )}
                  </div>
                </TabsContent>
              </Tabs>
            </div>
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
