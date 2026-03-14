"use client"

import { useState } from "react"
import { AppSidebar } from "@/components/app-sidebar"
import { PageHeader } from "@/components/page-header"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"

const PROPOSAL_STEPS = [
  { id: "basic-info", label: "Basic Info" },
  { id: "location", label: "Location" },
  { id: "specification", label: "Specification" },
  { id: "economics", label: "Economics" },
] as const

type StepId = (typeof PROPOSAL_STEPS)[number]["id"]

export default function NewProposalPage() {
  const [activeStepId, setActiveStepId] = useState<StepId>(PROPOSAL_STEPS[0].id)
  const currentIndex = PROPOSAL_STEPS.findIndex((s) => s.id === activeStepId)
  const canGoPrev = currentIndex > 0
  const canGoNext = currentIndex < PROPOSAL_STEPS.length - 1

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
                {PROPOSAL_STEPS.map((step) => (
                  <TabsContent
                    key={step.id}
                    value={step.id}
                    className="mt-4 rounded-lg border bg-card p-4 md:p-6"
                  >
                    <h2 className="text-lg font-semibold text-foreground md:text-xl">
                      {step.label}
                    </h2>
                    <p className="mt-2 text-sm text-muted-foreground">
                      Content for this step will go here.
                    </p>
                    <div className="mt-6 flex gap-2">
                      <Button
                        variant="outline"
                        size="lg"
                        onClick={() =>
                          canGoPrev &&
                          setActiveStepId(PROPOSAL_STEPS[currentIndex - 1].id)
                        }
                        disabled={!canGoPrev}
                      >
                        Previous
                      </Button>
                      <Button
                        size="lg"
                        onClick={() =>
                          canGoNext &&
                          setActiveStepId(PROPOSAL_STEPS[currentIndex + 1].id)
                        }
                        disabled={!canGoNext}
                      >
                        Next
                      </Button>
                    </div>
                  </TabsContent>
                ))}
              </Tabs>
            </div>
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
