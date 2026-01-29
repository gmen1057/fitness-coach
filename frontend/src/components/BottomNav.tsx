"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home,
  Dumbbell,
  MessageCircle,
  ListChecks,
  TrendingUp,
} from "lucide-react";
import { clsx } from "clsx";

const navItems = [
  { href: "/", label: "Home", icon: Home },
  { href: "/workout", label: "Workout", icon: Dumbbell },
  { href: "/progress", label: "Progress", icon: TrendingUp },
  { href: "/plans", label: "Plans", icon: ListChecks },
  { href: "/chat", label: "Chat", icon: MessageCircle },
];

export function BottomNav() {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/") {
      return pathname === "/";
    }
    return pathname.startsWith(href);
  };

  return (
    <nav className="fixed bottom-4 left-4 right-4 z-50">
      <div className="bg-white/95 dark:bg-gray-800/95 backdrop-blur-xl rounded-full shadow-2xl border border-gray-200/50 dark:border-gray-700/50">
        <div className="flex items-center justify-around gap-1 px-2">
          {navItems.map((item) => {
            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  "relative flex flex-col items-center justify-center",
                  "flex-1 min-h-[56px] py-2 px-2",
                  "rounded-full transition-all duration-300",
                  active
                    ? "text-fitness"
                    : "text-gray-400 dark:text-gray-500"
                )}
              >
                {/* Active indicator background - Material You style */}
                {active && (
                  <div className="absolute inset-0 rounded-full animate-fade-in bg-fitness/10 dark:bg-fitness/20" />
                )}

                {/* Icon with active scaling */}
                <div className="relative z-10 transition-transform duration-300">
                  <item.icon
                    className={clsx(
                      "w-6 h-6 transition-all duration-300",
                      active ? "stroke-[2.5px] scale-110" : "stroke-[1.5px]"
                    )}
                  />
                  {/* Active indicator dot */}
                  {active && (
                    <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full animate-fade-in bg-fitness" />
                  )}
                </div>

                <span
                  className={clsx(
                    "text-[10px] mt-1.5 relative z-10 transition-all duration-300",
                    active ? "font-bold opacity-100" : "font-medium opacity-70"
                  )}
                >
                  {item.label}
                </span>
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
