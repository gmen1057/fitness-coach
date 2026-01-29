"use client";

import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { clsx } from "clsx";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[];
  className?: string;
}

export function Breadcrumbs({ items, className }: BreadcrumbsProps) {
  if (items.length === 0) return null;

  return (
    <nav
      className={clsx(
        "flex items-center gap-1 text-xs overflow-x-auto scrollbar-hide",
        className
      )}
      aria-label="Breadcrumb"
    >
      {items.map((item, index) => {
        const isLast = index === items.length - 1;

        return (
          <div key={index} className="flex items-center gap-1 flex-shrink-0">
            {index > 0 && (
              <ChevronRight className="w-3 h-3 text-gray-400 flex-shrink-0" />
            )}
            {item.href && !isLast ? (
              <Link
                href={item.href}
                className="text-gray-500 dark:text-gray-400 hover:text-fitness transition-colors truncate max-w-[100px]"
              >
                {item.label}
              </Link>
            ) : (
              <span
                className={clsx(
                  "truncate max-w-[120px]",
                  isLast
                    ? "text-gray-900 dark:text-white font-medium"
                    : "text-gray-500 dark:text-gray-400"
                )}
              >
                {item.label}
              </span>
            )}
          </div>
        );
      })}
    </nav>
  );
}
