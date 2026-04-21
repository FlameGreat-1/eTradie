import { memo, type ReactNode } from 'react';
import Sidebar from './Sidebar';
import Header from './Header';
import { SIDEBAR_WIDTH, HEADER_HEIGHT } from '@/utils/constants';

interface Props {
  children: ReactNode;
}

function DashboardLayout({ children }: Props) {
  return (
    <div className="fixed inset-0 w-screen h-screen overflow-hidden bg-surface-0">
      <Sidebar />
      <Header />
      <main
        className="absolute overflow-auto bg-surface-0"
        style={{
          left: SIDEBAR_WIDTH,
          top: HEADER_HEIGHT,
          right: 0,
          bottom: 0,
        }}
      >
        {children}
      </main>
    </div>
  );
}

export default memo(DashboardLayout);
