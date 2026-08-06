"use client";

import React, { useState, useMemo } from "react";
import {
  Search,
  ChevronDown,
  ChevronUp,
  ChevronsUpDown,
  ChevronLeft,
  ChevronRight,
  Calendar,
  Filter,
  RefreshCw,
  SlidersHorizontal,
  X
} from "lucide-react";
import { getRolePriority, getStatusPriority } from "@/lib/roles";

export interface ColumnDef<T> {
  key: string;
  label: string;
  sortable?: boolean;
  align?: "left" | "center" | "right";
  render?: (row: T) => React.ReactNode;
}

export interface FilterOption {
  key: string;
  label: string;
  options: { label: string; value: string }[];
}

export interface DataTableProps<T> {
  title?: string;
  subtitle?: string;
  columns: ColumnDef<T>[];
  data: T[];
  searchKeys?: (keyof T | string)[];
  searchPlaceholder?: string;
  defaultSortKey?: string;
  defaultSortDir?: "asc" | "desc";
  filterOptions?: FilterOption[];
  dateKey?: string; // key for date filtering (e.g., 'created_at')
  pageSizeOptions?: number[];
  defaultPageSize?: number;
  isLoading?: boolean;
  emptyStateText?: string;
  actions?: React.ReactNode;
  onRowClick?: (row: T) => void;
}

export function DataTable<T extends Record<string, any>>({
  title,
  subtitle,
  columns,
  data,
  searchKeys = [],
  searchPlaceholder = "Search records...",
  defaultSortKey,
  defaultSortDir = "asc",
  filterOptions = [],
  dateKey,
  pageSizeOptions = [10, 25, 50, 100],
  defaultPageSize = 10,
  isLoading = false,
  emptyStateText = "No records found.",
  actions,
  onRowClick
}: DataTableProps<T>) {
  const [searchQuery, setSearchQuery] = useState("");
  const [sortKey, setSortKey] = useState<string>(defaultSortKey || (columns[0]?.key ?? ""));
  const [sortDir, setSortDir] = useState<"asc" | "desc">(defaultSortDir);
  const [selectedFilters, setSelectedFilters] = useState<Record<string, string>>({});
  const [dateRange, setDateRange] = useState<string>("all"); // 'all', 'today', '7days', '30days', 'this_month'
  const [pageSize, setPageSize] = useState<number>(defaultPageSize);
  const [currentPage, setCurrentPage] = useState<number>(1);

  // 1. Debounced / Formatted Search Filtering
  const filteredData = useMemo(() => {
    let result = [...data];

    // Search filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter(item => {
        if (searchKeys.length > 0) {
          return searchKeys.some(k => {
            const val = item[k as string];
            if (val === null || val === undefined) return false;
            return String(val).toLowerCase().includes(q);
          });
        }
        // Fallback: search across all primitive values
        return Object.values(item).some(val => {
          if (val === null || val === undefined) return false;
          if (typeof val === "object") return false;
          return String(val).toLowerCase().includes(q);
        });
      });
    }

    // Dynamic Select Filters
    Object.entries(selectedFilters).forEach(([filterKey, filterVal]) => {
      if (filterVal && filterVal !== "ALL") {
        result = result.filter(item => {
          const itemVal = String(item[filterKey] || "").toUpperCase();
          return itemVal === filterVal.toUpperCase();
        });
      }
    });

    // Date Range Filter
    if (dateKey && dateRange !== "all") {
      const now = new Date();
      const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());

      result = result.filter(item => {
        const itemDateStr = item[dateKey];
        if (!itemDateStr) return false;
        const d = new Date(itemDateStr);
        if (isNaN(d.getTime())) return false;

        if (dateRange === "today") {
          return d >= todayStart;
        } else if (dateRange === "7days") {
          const sevenDaysAgo = new Date(todayStart.getTime() - 7 * 24 * 60 * 60 * 1000);
          return d >= sevenDaysAgo;
        } else if (dateRange === "30days") {
          const thirtyDaysAgo = new Date(todayStart.getTime() - 30 * 24 * 60 * 60 * 1000);
          return d >= thirtyDaysAgo;
        } else if (dateRange === "this_month") {
          const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
          return d >= monthStart;
        } else if (dateRange === "last_month") {
          const lastMonthStart = new Date(now.getFullYear(), now.getMonth() - 1, 1);
          const lastMonthEnd = new Date(now.getFullYear(), now.getMonth(), 0);
          return d >= lastMonthStart && d <= lastMonthEnd;
        } else if (dateRange === "this_year") {
          const yearStart = new Date(now.getFullYear(), 0, 1);
          return d >= yearStart;
        }
        return true;
      });
    }

    // Sorting
    if (sortKey) {
      result.sort((a, b) => {
        let valA = a[sortKey];
        let valB = b[sortKey];

        if (sortKey === "role") {
          const pA = getRolePriority(valA);
          const pB = getRolePriority(valB);
          if (pA !== pB) return sortDir === "asc" ? pA - pB : pB - pA;
        }

        if (sortKey === "status") {
          const pA = getStatusPriority(valA);
          const pB = getStatusPriority(valB);
          if (pA !== pB) return sortDir === "asc" ? pA - pB : pB - pA;
        }

        if (valA === null || valA === undefined) valA = "";
        if (valB === null || valB === undefined) valB = "";

        // Handle string comparison vs date / number
        if (typeof valA === "number" && typeof valB === "number") {
          return sortDir === "asc" ? valA - valB : valB - valA;
        }

        const strA = String(valA).toLowerCase();
        const strB = String(valB).toLowerCase();

        if (strA < strB) return sortDir === "asc" ? -1 : 1;
        if (strA > strB) return sortDir === "asc" ? 1 : -1;
        return 0;
      });
    }

    return result;
  }, [data, searchQuery, searchKeys, selectedFilters, dateKey, dateRange, sortKey, sortDir]);

  // Pagination calculations
  const totalRecords = filteredData.length;
  const totalPages = Math.max(1, Math.ceil(totalRecords / pageSize));
  const validPage = Math.min(currentPage, totalPages);

  const paginatedData = useMemo(() => {
    const start = (validPage - 1) * pageSize;
    return filteredData.slice(start, start + pageSize);
  }, [filteredData, validPage, pageSize]);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir(prev => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const handleFilterChange = (key: string, val: string) => {
    setSelectedFilters(prev => ({ ...prev, [key]: val }));
    setCurrentPage(1);
  };

  const resetFilters = () => {
    setSearchQuery("");
    setSelectedFilters({});
    setDateRange("all");
    setCurrentPage(1);
  };

  const hasActiveFilters = searchQuery.trim() !== "" || Object.values(selectedFilters).some(v => v && v !== "ALL") || dateRange !== "all";

  return (
    <div className="w-full space-y-4">
      {/* Header & Title bar */}
      {(title || subtitle || actions) && (
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            {title && <h2 className="text-lg font-bold text-[var(--color-text-primary)]">{title}</h2>}
            {subtitle && <p className="text-xs text-[var(--color-text-secondary)]">{subtitle}</p>}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}

      {/* Control Toolbar: Search, Select Filters, Date Range, Reset */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-3 shadow-sm flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        {/* Search Input */}
        <div className="relative flex-1 min-w-[240px]">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
          <input
            type="text"
            value={searchQuery}
            onChange={e => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            placeholder={searchPlaceholder}
            className="w-full pl-9 pr-8 py-2 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-emerald-500 focus:ring-1"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
            >
              <X size={14} />
            </button>
          )}
        </div>

        {/* Filters & Options */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Custom Select Filters */}
          {filterOptions.map(filter => (
            <select
              key={filter.key}
              value={selectedFilters[filter.key] || "ALL"}
              onChange={e => handleFilterChange(filter.key, e.target.value)}
              className="py-2 px-3 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500"
            >
              <option value="ALL">{filter.label}: All</option>
              {filter.options.map(opt => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          ))}

          {/* Date Range Selector (if dateKey provided) */}
          {dateKey && (
            <div className="relative flex items-center">
              <Calendar size={14} className="absolute left-2.5 text-[var(--color-text-muted)] pointer-events-none" />
              <select
                value={dateRange}
                onChange={e => {
                  setDateRange(e.target.value);
                  setCurrentPage(1);
                }}
                className="pl-8 pr-3 py-2 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-emerald-500"
              >
                <option value="all">Date: All Time</option>
                <option value="today">Today</option>
                <option value="7days">Last 7 Days</option>
                <option value="30days">Last 30 Days</option>
                <option value="this_month">This Month</option>
              </select>
            </div>
          )}

          {/* Reset Filters */}
          {hasActiveFilters && (
            <button
              onClick={resetFilters}
              className="px-2.5 py-2 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500/20 text-xs flex items-center gap-1.5 transition-colors"
              title="Reset all filters"
            >
              <RefreshCw size={12} />
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Main Table View */}
      <div className="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl overflow-hidden shadow-md">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[var(--color-surface)] border-b border-[var(--color-border)] text-[11px] font-bold text-[var(--color-text-secondary)] uppercase tracking-wider">
                {columns.map(col => (
                  <th
                    key={col.key}
                    onClick={() => col.sortable !== false && handleSort(col.key)}
                    className={`py-3 px-4 transition-colors ${
                      col.sortable !== false ? "cursor-pointer hover:text-[var(--color-text-primary)] select-none" : ""
                    } ${col.align === "right" ? "text-right" : col.align === "center" ? "text-center" : "text-left"}`}
                  >
                    <div
                      className={`flex items-center gap-1.5 ${
                        col.align === "right" ? "justify-end" : col.align === "center" ? "justify-center" : "justify-start"
                      }`}
                    >
                      <span>{col.label}</span>
                      {col.sortable !== false && (
                        <span>
                          {sortKey === col.key ? (
                            sortDir === "asc" ? (
                              <ChevronUp size={14} className="text-emerald-400" />
                            ) : (
                              <ChevronDown size={14} className="text-emerald-400" />
                            )
                          ) : (
                            <ChevronsUpDown size={12} className="text-[var(--color-text-muted)] opacity-50" />
                          )}
                        </span>
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border)] text-xs text-[var(--color-text-primary)]">
              {isLoading ? (
                Array.from({ length: 5 }).map((_, idx) => (
                  <tr key={idx} className="animate-pulse">
                    {columns.map(col => (
                      <td key={col.key} className="py-4 px-4">
                        <div className="h-4 bg-[var(--color-surface)] rounded w-3/4" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : paginatedData.length > 0 ? (
                paginatedData.map((row, rowIdx) => (
                  <tr
                    key={row.id || row._id || rowIdx}
                    onClick={() => onRowClick && onRowClick(row)}
                    className={`transition-colors hover:bg-[var(--color-surface)]/50 ${
                      onRowClick ? "cursor-pointer" : ""
                    }`}
                  >
                    {columns.map(col => (
                      <td
                        key={col.key}
                        className={`py-3.5 px-4 ${
                          col.align === "right"
                            ? "text-right"
                            : col.align === "center"
                            ? "text-center"
                            : "text-left"
                        }`}
                      >
                        {col.render ? col.render(row) : String(row[col.key] ?? "—")}
                      </td>
                    ))}
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={columns.length} className="py-12 text-center text-[var(--color-text-muted)]">
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <Filter size={24} className="opacity-40 text-emerald-400" />
                      <p className="text-sm font-medium">{emptyStateText}</p>
                      {hasActiveFilters && (
                        <button
                          onClick={resetFilters}
                          className="text-xs text-emerald-400 hover:underline pt-1"
                        >
                          Clear active search & filters
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Footer Pagination Bar */}
        <div className="bg-[var(--color-surface)] border-t border-[var(--color-border)] px-4 py-3 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-[var(--color-text-secondary)]">
          <div className="flex items-center gap-4">
            <span>
              Showing{" "}
              <strong className="text-[var(--color-text-primary)]">
                {totalRecords > 0 ? (validPage - 1) * pageSize + 1 : 0}
              </strong>{" "}
              to{" "}
              <strong className="text-[var(--color-text-primary)]">
                {Math.min(validPage * pageSize, totalRecords)}
              </strong>{" "}
              of <strong className="text-[var(--color-text-primary)]">{totalRecords}</strong> records
            </span>

            {/* Page Size Selector */}
            <div className="flex items-center gap-1.5">
              <span>Per page:</span>
              <select
                value={pageSize}
                onChange={e => {
                  setPageSize(Number(e.target.value));
                  setCurrentPage(1);
                }}
                className="py-1 px-2 rounded border border-[var(--color-border)] bg-[var(--color-background)] text-xs text-[var(--color-text-primary)] focus:outline-none"
              >
                {pageSizeOptions.map(opt => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Page Navigation Controls */}
          <div className="flex items-center gap-1">
            <button
              disabled={validPage <= 1}
              onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
              className="p-1.5 rounded-lg border border-[var(--color-border)] text-[var(--color-text-primary)] hover:bg-[var(--color-background)] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              title="Previous Page"
            >
              <ChevronLeft size={16} />
            </button>
            <span className="px-3 py-1 font-medium text-[var(--color-text-primary)]">
              Page {validPage} of {totalPages}
            </span>
            <button
              disabled={validPage >= totalPages}
              onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
              className="p-1.5 rounded-lg border border-[var(--color-border)] text-[var(--color-text-primary)] hover:bg-[var(--color-background)] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              title="Next Page"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
