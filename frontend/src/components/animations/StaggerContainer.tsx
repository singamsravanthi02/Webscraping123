'use client';

import { motion, HTMLMotionProps } from 'framer-motion';
import { ReactNode } from 'react';

interface StaggerContainerProps extends HTMLMotionProps<"div"> {
  children: ReactNode;
  staggerDelay?: number;
  delayChildren?: number;
}

export function StaggerContainer({ 
  children, 
  staggerDelay = 0.1, 
  delayChildren = 0,
  ...props 
}: StaggerContainerProps) {
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      exit="hidden"
      variants={{
        hidden: { opacity: 0 },
        visible: {
          opacity: 1,
          transition: {
            staggerChildren: staggerDelay,
            delayChildren: delayChildren,
          },
        },
      }}
      {...props}
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({ children, className }: { children: ReactNode, className?: string }) {
  return (
    <motion.div
      variants={{
        hidden: { opacity: 0, y: 20 },
        visible: { opacity: 1, y: 0, transition: { ease: [0.22, 1, 0.36, 1], duration: 0.6 } }
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
