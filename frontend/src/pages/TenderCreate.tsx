import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { FilePlus2, FileText, Hash, Building2 } from 'lucide-react'
import Layout from '../components/Layout'
import {
  PageHeader,
  SectionCard,
  FormField,
  Input,
  Textarea,
  Button,
  Alert,
} from '../components/ui'
import { createTender } from '../api/tenders'
import { getErrorMessage } from '../lib/errors'

export default function TenderCreate() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    tender_ref_no: '',
    title: '',
    department: '',
    description: '',
    tender_date: '',
    deadline: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  function update(field: keyof typeof form, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)
    try {
      const tender = await createTender({
        tender_ref_no: form.tender_ref_no,
        title: form.title,
        department: form.department || undefined,
        description: form.description || undefined,
        tender_date: form.tender_date ? new Date(form.tender_date).toISOString() : undefined,
        deadline: form.deadline ? new Date(form.deadline).toISOString() : undefined,
      })
      navigate(`/tenders/${tender.id}`)
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to create tender'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Layout>
      <PageHeader
        icon={<FilePlus2 className="h-5 w-5" />}
        title="New tender"
        description="Enter tender metadata now — you'll upload the tender PDF and run AI extraction on the next screen."
        breadcrumbs={[{ label: 'Tenders', to: '/tenders' }, { label: 'New tender' }]}
      />

      <div className="mx-auto max-w-2xl">
        <SectionCard
          icon={<FileText className="h-4 w-4" />}
          title="Tender details"
          description="Fields marked with * are required."
        >
          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <Alert variant="danger" onDismiss={() => setError(null)}>
                {error}
              </Alert>
            )}

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FormField label="Tender reference no." htmlFor="tender_ref_no" required>
                <Input
                  id="tender_ref_no"
                  required
                  value={form.tender_ref_no}
                  onChange={(e) => update('tender_ref_no', e.target.value)}
                  placeholder="GEM/2026/B/1234567"
                  leftIcon={<Hash className="h-4 w-4" />}
                />
              </FormField>

              <FormField label="Department" htmlFor="department">
                <Input
                  id="department"
                  value={form.department}
                  onChange={(e) => update('department', e.target.value)}
                  placeholder="Materials & Procurement"
                  leftIcon={<Building2 className="h-4 w-4" />}
                />
              </FormField>
            </div>

            <FormField label="Title" htmlFor="title" required>
              <Input
                id="title"
                required
                value={form.title}
                onChange={(e) => update('title', e.target.value)}
                placeholder="Supply of Industrial Valves and Fittings"
              />
            </FormField>

            <FormField
              label="Description"
              htmlFor="description"
              hint="Optional. A short summary of the tender scope."
            >
              <Textarea
                id="description"
                rows={3}
                value={form.description}
                onChange={(e) => update('description', e.target.value)}
                placeholder="Brief description of goods or services being procured…"
              />
            </FormField>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FormField label="Tender date" htmlFor="tender_date">
                <Input
                  id="tender_date"
                  type="date"
                  value={form.tender_date}
                  onChange={(e) => update('tender_date', e.target.value)}
                />
              </FormField>

              <FormField label="Bid deadline" htmlFor="deadline">
                <Input
                  id="deadline"
                  type="date"
                  value={form.deadline}
                  onChange={(e) => update('deadline', e.target.value)}
                />
              </FormField>
            </div>

            <div className="flex flex-col-reverse gap-3 border-t border-slate-200 pt-5 sm:flex-row sm:justify-end">
              <Button type="button" variant="outline" onClick={() => navigate('/tenders')}>
                Cancel
              </Button>
              <Button type="submit" loading={isSubmitting} leftIcon={<FilePlus2 className="h-4 w-4" />}>
                {isSubmitting ? 'Creating…' : 'Create tender'}
              </Button>
            </div>
          </form>
        </SectionCard>
      </div>
    </Layout>
  )
}
