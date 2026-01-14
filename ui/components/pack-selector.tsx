'use client'

import { usePack, Pack } from '@/lib/pack-context'
import { Button } from '@/components/ui/button'
import { Building2, Wallet } from 'lucide-react'

const PACK_CONFIG: Record<Pack, { label: string; icon: typeof Building2 }> = {
  treasury: {
    label: 'Treasury',
    icon: Building2,
  },
  wealth: {
    label: 'Wealth',
    icon: Wallet,
  },
}

export function PackSelector() {
  const { pack, setPack } = usePack()

  return (
    <div className="flex items-center gap-1 bg-muted rounded-lg p-1">
      {(Object.keys(PACK_CONFIG) as Pack[]).map((p) => {
        const config = PACK_CONFIG[p]
        const Icon = config.icon
        const isActive = pack === p

        return (
          <Button
            key={p}
            variant={isActive ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setPack(p)}
            className={`gap-2 ${isActive ? '' : 'text-muted-foreground'}`}
          >
            <Icon className="h-4 w-4" />
            {config.label}
          </Button>
        )
      })}
    </div>
  )
}
