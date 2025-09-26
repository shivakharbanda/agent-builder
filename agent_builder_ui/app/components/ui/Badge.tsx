import React from 'react';
import { cn, getStatusBgColor } from '../../lib/utils';

interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'success' | 'warning' | 'error' | 'info';
  status?: string;
}

export function Badge({
  className,
  variant = 'default',
  status,
  children,
  ...props
}: BadgeProps) {
  const variants = {
    default: 'bg-[#233648] text-gray-300',
    secondary: 'bg-gray-500/10 text-gray-400',
    success: 'bg-green-500/10 text-green-500',
    warning: 'bg-yellow-500/10 text-yellow-500',
    error: 'bg-red-500/10 text-red-500',
    info: 'bg-blue-500/10 text-blue-500',
  };

  const statusColor = status ? getStatusBgColor(status) : '';

  return (
    <div
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        status ? statusColor : variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}