import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

export const registerSchema = z.object({
  name: z.string().optional(),
  email: z.string().email("Enter a valid work email"),
  password: z.string().min(8, "Use at least 8 characters"),
});

export const forgotPasswordSchema = z.object({
  email: z.string().email("Enter a valid email"),
});

export type LoginValues = z.infer<typeof loginSchema>;
export type RegisterValues = z.infer<typeof registerSchema>;
export type ForgotPasswordValues = z.infer<typeof forgotPasswordSchema>;
