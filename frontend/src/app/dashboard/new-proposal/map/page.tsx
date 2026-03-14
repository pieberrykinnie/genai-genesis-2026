"use client"

import Link from "next/link"
import { AppSidebar } from "@/components/app-sidebar"
import { PageHeader } from "@/components/page-header"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { MapPinIcon } from "lucide-react"

export default function MapPickerPage() {
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
        <PageHeader title="Pick location on map" />
        <div className="flex flex-1 flex-col">
          <div className="@container/main flex flex-1 flex-col gap-2">
            <div className="mx-auto w-full max-w-5xl flex flex-col gap-6 px-4 py-6 md:px-6 md:py-8">
              <Card className="max-w-xl">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <MapPinIcon className="size-5" />
                    Map picker
                  </CardTitle>
                  <CardDescription>
                    MapTiler integration will go here: full-screen map, place
                    pin, confirm to save lat/lng back to the proposal form.
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex gap-2">
                  <Button asChild variant="outline" size="lg">
                    <Link href="/dashboard/new-proposal">Cancel</Link>
                  </Button>
                  <Button asChild size="lg">
                    <Link href="/dashboard/new-proposal">
                      Back to form (placeholder)
                    </Link>
                  </Button>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
