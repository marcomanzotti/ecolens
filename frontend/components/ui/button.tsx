import { Button as ButtonPrimitive } from "@base-ui/react/button"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "cn"

/* Brand rule: text sits only on Deep Blue, Electric Blue or white. */
const buttonVariants = cva(
  "inline-flex shrink-0 cursor-pointer items-center justify-center gap-2 rounded-md border font-bold whitespace-nowrap transition-[background-color,border-color,transform] duration-150 select-none active:scale-[0.97] disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "border-primary bg-primary text-primary-foreground hover:bg-primary/85",
        accent: "border-neon bg-transparent text-neon hover:bg-electric",
        outline: "border-line-strong bg-transparent text-foreground hover:border-foreground hover:bg-electric",
        ghost: "border-transparent bg-transparent text-foreground hover:bg-electric",
        link: "h-auto border-transparent p-0 text-foreground underline underline-offset-4 hover:text-neon",
      },
      size: {
        default: "min-h-11 px-4 text-base",
        sm: "min-h-9 px-3 text-sm",
        lg: "min-h-12 px-6 text-lg",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
