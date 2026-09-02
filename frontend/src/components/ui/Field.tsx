import { forwardRef } from 'react'
import type {
  InputHTMLAttributes,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
  ReactNode,
  LabelHTMLAttributes,
} from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '../../lib/cn'

const CONTROL_BASE =
  'w-full rounded-lg border bg-white text-sm text-slate-900 placeholder:text-slate-400 shadow-sm transition-colors focus:outline-none disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500'

function controlState(invalid?: boolean) {
  return invalid
    ? 'border-danger-300 focus:border-danger-500 focus:ring-2 focus:ring-danger-500/30'
    : 'border-slate-300 hover:border-slate-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30'
}

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean
  leftIcon?: ReactNode
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { invalid, leftIcon, className, ...rest },
  ref,
) {
  if (leftIcon) {
    return (
      <div className="relative">
        <span className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
          {leftIcon}
        </span>
        <input
          ref={ref}
          className={cn(CONTROL_BASE, controlState(invalid), 'h-10 pl-9 pr-3', className)}
          {...rest}
        />
      </div>
    )
  }
  return (
    <input
      ref={ref}
      className={cn(CONTROL_BASE, controlState(invalid), 'h-10 px-3', className)}
      {...rest}
    />
  )
})

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { invalid, className, rows = 4, ...rest },
  ref,
) {
  return (
    <textarea
      ref={ref}
      rows={rows}
      className={cn(CONTROL_BASE, controlState(invalid), 'px-3 py-2', className)}
      {...rest}
    />
  )
})

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  invalid?: boolean
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { invalid, className, children, ...rest },
  ref,
) {
  return (
    <div className="relative">
      <select
        ref={ref}
        className={cn(
          CONTROL_BASE,
          controlState(invalid),
          'h-10 cursor-pointer appearance-none pl-3 pr-9',
          className,
        )}
        {...rest}
      >
        {children}
      </select>
      <ChevronDown
        className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
        aria-hidden="true"
      />
    </div>
  )
})

export interface LabelProps extends LabelHTMLAttributes<HTMLLabelElement> {
  required?: boolean
}

export function Label({ required, className, children, ...rest }: LabelProps) {
  return (
    <label className={cn('block text-sm font-medium text-slate-700', className)} {...rest}>
      {children}
      {required ? <span className="ml-0.5 text-danger-500">*</span> : null}
    </label>
  )
}

interface FormFieldProps {
  label?: ReactNode
  htmlFor?: string
  required?: boolean
  error?: string | null
  hint?: ReactNode
  className?: string
  children: ReactNode
}

/** Label + control + hint/error wrapper for consistent form rows. */
export function FormField({
  label,
  htmlFor,
  required,
  error,
  hint,
  className,
  children,
}: FormFieldProps) {
  return (
    <div className={cn('space-y-1.5', className)}>
      {label ? (
        <Label htmlFor={htmlFor} required={required}>
          {label}
        </Label>
      ) : null}
      {children}
      {error ? (
        <p className="text-xs font-medium text-danger-600">{error}</p>
      ) : hint ? (
        <p className="text-xs text-slate-500">{hint}</p>
      ) : null}
    </div>
  )
}
