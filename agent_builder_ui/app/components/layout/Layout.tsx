import React from 'react';
import { Header } from './Header';

interface LayoutProps {
  children: React.ReactNode;
  fullHeight?: boolean;
}

export function Layout({ children, fullHeight = false }: LayoutProps) {
  return (
    <div className="relative flex h-auto min-h-screen w-full flex-col bg-[#111a22] dark group/design-root overflow-x-hidden">
      <div className="layout-container flex h-full grow flex-col">
        <Header />
        <main className={fullHeight ? "flex-1" : "flex-1 px-4 sm:px-6 lg:px-10 py-4 sm:py-6 lg:py-8"}>
          {children}
        </main>
      </div>
    </div>
  );
}