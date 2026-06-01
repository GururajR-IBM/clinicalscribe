import { z } from 'zod';

export const EncounterStatus = z.enum([
  'draft',
  'ingesting',
  'agent_running',
  'awaiting_review',
  'signed',
  'archived',
  'failed',
]);
export type EncounterStatus = z.infer<typeof EncounterStatus>;

export const Encounter = z.object({
  id: z.string().uuid(),
  patientId: z.string().uuid(),
  clinicianId: z.string().uuid(),
  status: EncounterStatus.default('draft'),
  title: z.string().min(1).max(200),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
});
export type Encounter = z.infer<typeof Encounter>;
