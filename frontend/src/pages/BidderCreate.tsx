import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Building2, UserPlus, FileText, Hash, Phone, Mail } from 'lucide-react'
import Layout from '../components/Layout'
import {
  PageHeader,
  SectionCard,
  FormField,
  Input,
  Button,
  Alert,
} from '../components/ui'
import { createBidder } from '../api/bidders'
import { getErrorMessage } from '../lib/errors'

export default function BidderCreate() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const tenderId = searchParams.get('tender_id') || ''

  const [form, setForm] = useState({
    company_name: '',
    gem_seller_id: '',
    contact_email: '',
    contact_phone: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  function update(field: keyof typeof form, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!tenderId) {
      setError('No tender selected. Go to a tender and click "Add Bidder" from there.')
      return
    }
    setError(null)
    setIsSubmitting(true)
    try {
      const bidder = await createBidder({
        tender_id: tenderId,
        company_name: form.company_name,
        gem_seller_id: form.gem_seller_id || undefined,
        contact_email: form.contact_email || undefined,
        contact_phone: form.contact_phone || undefined,
      })
      navigate(`/bidders/${bidder.id}`)
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to create bidder'))
    } finally {
      setIsSubmitting(false)
    }
  }

  const biddersHref = tenderId ? `/bidders?tender_id=${tenderId}` : '/bidders'

  return (
    <Layout>
      <PageHeader
        icon={<UserPlus className="h-5 w-5" />}
        title="Add bidder"
        description="Register a bidder against this tender — you'll upload their eligibility documents on the next screen."
        breadcrumbs={[{ label: 'Bidders', to: biddersHref }, { label: 'Add bidder' }]}
      />

      <div className="mx-auto max-w-2xl">
        {!tenderId && (
          <Alert variant="warning" title="No tender selected" className="mb-6">
            Open a tender first and choose “Add Bidder” from there, so the bidder is linked to the
            correct tender.
            <div className="mt-3">
              <Button variant="outline" size="sm" onClick={() => navigate('/tenders')}>
                Go to tenders
              </Button>
            </div>
          </Alert>
        )}

        <SectionCard
          icon={<Building2 className="h-4 w-4" />}
          title="Bidder details"
          description="Company identity and point of contact for this submission."
        >
          <form onSubmit={handleSubmit} className="space-y-5" noValidate>
            {error && (
              <Alert variant="danger" onDismiss={() => setError(null)}>
                {error}
              </Alert>
            )}

            {tenderId && (
              <FormField
                label="Tender"
                htmlFor="tender"
                hint="This bidder will be registered against the selected tender."
              >
                <Input
                  id="tender"
                  value={tenderId}
                  readOnly
                  disabled
                  leftIcon={<FileText className="h-4 w-4" />}
                  className="font-mono text-xs"
                />
              </FormField>
            )}

            <FormField label="Company name" htmlFor="company_name" required>
              <Input
                id="company_name"
                required
                value={form.company_name}
                onChange={(e) => update('company_name', e.target.value)}
                placeholder="ABC Industries Pvt Ltd"
              />
            </FormField>

            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
              <FormField label="GeM Seller ID" htmlFor="gem_seller_id">
                <Input
                  id="gem_seller_id"
                  value={form.gem_seller_id}
                  onChange={(e) => update('gem_seller_id', e.target.value)}
                  placeholder="SLR000123456"
                  leftIcon={<Hash className="h-4 w-4" />}
                />
              </FormField>

              <FormField label="Contact phone" htmlFor="contact_phone">
                <Input
                  id="contact_phone"
                  value={form.contact_phone}
                  onChange={(e) => update('contact_phone', e.target.value)}
                  placeholder="+91 98765 43210"
                  leftIcon={<Phone className="h-4 w-4" />}
                />
              </FormField>
            </div>

            <FormField label="Contact email" htmlFor="contact_email">
              <Input
                id="contact_email"
                type="email"
                value={form.contact_email}
                onChange={(e) => update('contact_email', e.target.value)}
                placeholder="contact@abcindustries.in"
                leftIcon={<Mail className="h-4 w-4" />}
              />
            </FormField>

            <div className="flex items-center justify-end gap-3 border-t border-slate-100 pt-5">
              <Button variant="outline" type="button" onClick={() => navigate(-1)}>
                Cancel
              </Button>
              <Button
                type="submit"
                loading={isSubmitting}
                disabled={!tenderId}
                leftIcon={<UserPlus className="h-4 w-4" />}
              >
                {isSubmitting ? 'Creating…' : 'Add bidder'}
              </Button>
            </div>
          </form>
        </SectionCard>
      </div>
    </Layout>
  )
}
