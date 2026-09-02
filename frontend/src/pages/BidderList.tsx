import { useEffect, useState, useMemo, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Building2, Plus, Search, FileX2 } from 'lucide-react'
import Layout from '../components/Layout'
import BidderConsistencyStatusBadge from '../components/BidderConsistencyStatusBadge'
import {
  PageHeader,
  Card,
  DataTable,
  FilterBar,
  Input,
  Button,
  EmptyState,
  ErrorState,
} from '../components/ui'
import type { Column } from '../components/ui'
import { listBidders } from '../api/bidders'
import { getTender } from '../api/tenders'
import type { Bidder, Tender } from '../types'
import { useAuth } from '../context/AuthContext'
import { canManage } from '../lib/roles'
import { getErrorMessage } from '../lib/errors'
import { formatDate } from '../lib/format'

export default function BidderList() {
  const [searchParams] = useSearchParams()
  const tenderId = searchParams.get('tender_id') || undefined
  const navigate = useNavigate()
  const { user } = useAuth()

  const [bidders, setBidders] = useState<Bidder[]>([])
  const [tender, setTender] = useState<Tender | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  const load = useCallback(() => {
    setIsLoading(true)
    setError(null)
    Promise.all([listBidders(tenderId), tenderId ? getTender(tenderId) : Promise.resolve(null)])
      .then(([b, t]) => {
        setBidders(b)
        setTender(t)
      })
      .catch((err) => setError(getErrorMessage(err, 'Failed to load bidders')))
      .finally(() => setIsLoading(false))
  }, [tenderId])

  useEffect(() => {
    load()
  }, [load])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return bidders
    return bidders.filter(
      (b) =>
        b.company_name.toLowerCase().includes(q) ||
        (b.gem_seller_id ?? '').toLowerCase().includes(q),
    )
  }, [bidders, search])

  const columns = useMemo<Column<Bidder>[]>(
    () => [
      {
        key: 'company_name',
        header: 'Company',
        render: (b) => (
          <div className="min-w-0">
            <p className="font-medium text-slate-800">{b.company_name}</p>
            <p className="truncate text-xs text-slate-400">
              {b.gem_seller_id ? `GeM: ${b.gem_seller_id}` : 'No GeM Seller ID'}
            </p>
          </div>
        ),
      },
      {
        key: 'consistency_status',
        header: 'Consistency',
        render: (b) => <BidderConsistencyStatusBadge status={b.consistency_status} />,
      },
      {
        key: 'contact',
        header: 'Contact',
        hideOnMobile: true,
        render: (b) =>
          b.contact_email || b.contact_phone ? (
            <div className="text-xs text-slate-500">
              {b.contact_email && <p className="truncate">{b.contact_email}</p>}
              {b.contact_phone && <p>{b.contact_phone}</p>}
            </div>
          ) : (
            <span className="text-slate-400">—</span>
          ),
      },
      {
        key: 'missing',
        header: 'Missing docs',
        align: 'center',
        hideOnMobile: true,
        render: (b) => {
          const n = b.missing_document_types?.length ?? 0
          return n > 0 ? (
            <span className="inline-flex items-center gap-1 font-semibold text-warning-700">
              <FileX2 className="h-3.5 w-3.5" />
              {n}
            </span>
          ) : (
            <span className="text-slate-400">—</span>
          )
        },
      },
      {
        key: 'created_at',
        header: 'Added',
        align: 'right',
        hideOnMobile: true,
        render: (b) => <span className="text-xs text-slate-500">{formatDate(b.created_at)}</span>,
      },
    ],
    [],
  )

  const breadcrumbs = tender
    ? [
        { label: 'Tenders', to: '/tenders' },
        { label: tender.tender_ref_no, to: `/tenders/${tender.id}` },
        { label: 'Bidders' },
      ]
    : [{ label: 'Bidders' }]

  return (
    <Layout>
      <PageHeader
        icon={<Building2 className="h-5 w-5" />}
        title="Bidders"
        description={
          tender ? `Bidders registered for “${tender.title}”.` : 'Every bidder across all tenders.'
        }
        breadcrumbs={breadcrumbs}
        actions={
          canManage(user) && tenderId ? (
            <Button
              leftIcon={<Plus className="h-4 w-4" />}
              onClick={() => navigate(`/bidders/new?tender_id=${tenderId}`)}
            >
              Add bidder
            </Button>
          ) : undefined
        }
      />

      {error ? (
        <ErrorState message={error} onRetry={load} />
      ) : (
        <Card flush>
          <FilterBar
            search={
              <Input
                type="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search company or GeM seller ID…"
                aria-label="Search bidders"
                leftIcon={<Search className="h-4 w-4" />}
              />
            }
          />

          <DataTable
            columns={columns}
            data={filtered}
            rowKey={(b) => b.id}
            onRowClick={(b) => navigate(`/bidders/${b.id}`)}
            loading={isLoading}
            skeletonRows={8}
            empty={
              <EmptyState
                icon={<Building2 className="h-6 w-6" />}
                title={bidders.length === 0 ? 'No bidders yet' : 'No matching bidders'}
                description={
                  bidders.length === 0
                    ? canManage(user) && tenderId
                      ? 'Add the first bidder to get started.'
                      : 'Bidders will appear here once they are added to a tender.'
                    : 'No bidders match your search.'
                }
                action={
                  bidders.length === 0 && canManage(user) && tenderId ? (
                    <Button
                      size="sm"
                      leftIcon={<Plus className="h-4 w-4" />}
                      onClick={() => navigate(`/bidders/new?tender_id=${tenderId}`)}
                    >
                      Add bidder
                    </Button>
                  ) : undefined
                }
              />
            }
          />
        </Card>
      )}
    </Layout>
  )
}
