import Link from "next/link"
import { ArrowRight } from "lucide-react"

export default function Home() {
  return (
    <div className="container mx-auto px-4 py-16">
      <div className="max-w-3xl mx-auto text-center space-y-8">
        <h1 className="text-4xl font-bold tracking-tight">
          Governance OS
        </h1>
        <p className="text-xl text-muted-foreground">
          Policy-driven coordination layer for high-stakes professional work
        </p>

        <div className="grid gap-4 md:grid-cols-3 pt-8">
          <Link
            href="/exceptions"
            className="group p-6 border rounded-lg hover:border-primary transition-colors"
          >
            <h2 className="text-lg font-semibold mb-2 flex items-center justify-between">
              Exceptions
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </h2>
            <p className="text-sm text-muted-foreground">
              View and resolve exceptions requiring human judgment
            </p>
          </Link>

          <Link
            href="/decisions"
            className="group p-6 border rounded-lg hover:border-primary transition-colors"
          >
            <h2 className="text-lg font-semibold mb-2 flex items-center justify-between">
              Decisions
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </h2>
            <p className="text-sm text-muted-foreground">
              Browse decision history with complete audit trail
            </p>
          </Link>

          <Link
            href="/policies"
            className="group p-6 border rounded-lg hover:border-primary transition-colors"
          >
            <h2 className="text-lg font-semibold mb-2 flex items-center justify-between">
              Policies
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </h2>
            <p className="text-sm text-muted-foreground">
              View active governance policies and rules
            </p>
          </Link>
        </div>

        <div className="pt-12 text-sm text-muted-foreground">
          <p>
            <strong>Core Loop:</strong> Signal → Policy Evaluation → Exception → Decision → Evidence/Outcome
          </p>
        </div>
      </div>
    </div>
  )
}
