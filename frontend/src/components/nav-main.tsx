"use client"

import Link from "next/link" // Import Next.js Link for client-side navigation
import { ChevronRight, type LucideIcon } from "lucide-react"
import { usePathname } from "next/navigation" // To determine active state

import { cn } from "@/lib/utils" // Assuming you have a cn utility for classnames
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
} from "@/components/ui/sidebar" // Assuming these are your custom/shadcn components

// Updated item type for clarity, url is always present at top level
export interface NavItem {
  title: string
  url: string // URL for direct navigation or base for collapsible
  icon?: LucideIcon
  items?: NavSubItem[] // Optional sub-items
  // isActive can be determined dynamically or passed in
}

export interface NavSubItem {
  title: string
  url: string
  // isActive can be determined dynamically or passed in
}

export function NavMain({ items }: { items: NavItem[] }) {
  const pathname = usePathname() // Get current path for active state

  return (
    <SidebarGroup>
      <SidebarGroupLabel>Platform</SidebarGroupLabel>
      <SidebarMenu>
        {items.map((item) => {
          const hasSubItems = item.items && item.items.length > 0
          // Determine if the top-level item itself is active (for direct links)
          // or if any of its sub-items are active (for opening collapsible)
          const isTopLevelActive = !hasSubItems && pathname === item.url
          const isAnySubItemActive =
            hasSubItems &&
            item.items?.some((subItem) => pathname === subItem.url)
          const shouldBeOpen = isAnySubItemActive // For collapsible

          if (hasSubItems) {
            // Item has sub-items, render as Collapsible
            return (
              <Collapsible
                key={item.title}
                asChild
                defaultOpen={shouldBeOpen} // Open if a sub-item is active
                className="group/collapsible"
              >
                <SidebarMenuItem>
                  <CollapsibleTrigger asChild>
                    <SidebarMenuButton
                      tooltip={item.title}
                      // Add active styling to trigger if needed, e.g., if section is active
                      // className={cn(isAnySubItemActive && "bg-accent")}
                    >
                      {item.icon && <item.icon className="h-5 w-5" />}
                      <span>{item.title}</span>
                      <ChevronRight className="ml-auto h-4 w-4 shrink-0 transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90" />
                    </SidebarMenuButton>
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <SidebarMenuSub>
                      {item.items?.map((subItem) => {
                        const isSubItemActive = pathname === subItem.url
                        return (
                          <SidebarMenuSubItem key={subItem.title}>
                            <SidebarMenuSubButton
                              asChild
                              className={cn(
                                isSubItemActive &&
                                  "bg-accent text-accent-foreground", // Active style for sub-item
                              )}
                            >
                              <Link href={subItem.url}>
                                <span>{subItem.title}</span>
                              </Link>
                            </SidebarMenuSubButton>
                          </SidebarMenuSubItem>
                        )
                      })}
                    </SidebarMenuSub>
                  </CollapsibleContent>
                </SidebarMenuItem>
              </Collapsible>
            )
          } else {
            // Item has no sub-items, render as a direct link
            return (
              <SidebarMenuItem key={item.title}>
                <SidebarMenuButton
                  asChild
                  tooltip={item.title}
                  className={cn(
                    isTopLevelActive && "bg-accent text-accent-foreground", // Active style for direct link
                  )}
                >
                  <Link href={item.url}>
                    {item.icon && <item.icon className="h-5 w-5" />}
                    <span>{item.title}</span>
                    {/* No ChevronRight icon for direct links */}
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            )
          }
        })}
      </SidebarMenu>
    </SidebarGroup>
  )
}
