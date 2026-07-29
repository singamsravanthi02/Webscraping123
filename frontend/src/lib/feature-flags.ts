const isEnabled = (value: string | undefined) => value === "true";

export const FEATURE_FLAGS = {
  emailVerification: isEnabled(process.env.NEXT_PUBLIC_ENABLE_EMAIL_VERIFICATION),
  googleAuth: isEnabled(process.env.NEXT_PUBLIC_ENABLE_GOOGLE_AUTH),
  forgotPassword: isEnabled(process.env.NEXT_PUBLIC_ENABLE_FORGOT_PASSWORD),
  learningRoadmap: isEnabled(process.env.NEXT_PUBLIC_ENABLE_LEARNING_ROADMAP),
} as const;
