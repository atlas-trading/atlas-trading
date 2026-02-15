import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

export type Network = 'testnet' | 'mainnet';

interface NetworkContextType {
  network: Network;
  toggleNetwork: () => void;
  setNetwork: (network: Network) => void;
}

const NetworkContext = createContext<NetworkContextType | undefined>(undefined);

export function NetworkProvider({ children }: { children: ReactNode }) {
  const [network, setNetworkState] = useState<Network>(() => {
    // Safe localStorage access
    try {
      if (typeof window !== 'undefined') {
        const saved = localStorage.getItem('network') as Network;
        if (saved === 'testnet' || saved === 'mainnet') {
          return saved;
        }
      }
    } catch (error) {
      console.warn('Failed to read network from localStorage:', error);
    }
    return 'testnet';
  });

  useEffect(() => {
    try {
      if (typeof window !== 'undefined') {
        localStorage.setItem('network', network);
      }
    } catch (error) {
      console.warn('Failed to save network to localStorage:', error);
    }
  }, [network]);

  const toggleNetwork = () => {
    setNetworkState(prev => prev === 'testnet' ? 'mainnet' : 'testnet');
  };

  const setNetwork = (newNetwork: Network) => {
    setNetworkState(newNetwork);
  };

  return (
    <NetworkContext.Provider value={{ network, toggleNetwork, setNetwork }}>
      {children}
    </NetworkContext.Provider>
  );
}

export function useNetwork() {
  const context = useContext(NetworkContext);
  if (!context) {
    throw new Error('useNetwork must be used within NetworkProvider');
  }
  return context;
}
