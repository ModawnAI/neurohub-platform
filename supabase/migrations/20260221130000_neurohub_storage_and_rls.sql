-- NeuroHub Supabase bootstrap: storage buckets + baseline RLS policy templates.

INSERT INTO storage.buckets (id, name, public)
VALUES
  ('neurohub-inputs', 'neurohub-inputs', false),
  ('neurohub-outputs', 'neurohub-outputs', false),
  ('neurohub-reports', 'neurohub-reports', false)
ON CONFLICT (id) DO NOTHING;

CREATE OR REPLACE FUNCTION public.current_institution_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
  SELECT NULLIF(auth.jwt() ->> 'institution_id', '')::uuid
$$;

DO $$
BEGIN
  IF to_regclass('public.requests') IS NOT NULL THEN
    EXECUTE 'ALTER TABLE public.requests ENABLE ROW LEVEL SECURITY';

    IF NOT EXISTS (
      SELECT 1 FROM pg_policies
      WHERE schemaname = 'public' AND tablename = 'requests' AND policyname = 'requests_select_same_institution'
    ) THEN
      EXECUTE '
        CREATE POLICY requests_select_same_institution
        ON public.requests
        FOR SELECT
        TO authenticated
        USING (institution_id = public.current_institution_id())
      ';
    END IF;
  END IF;

  IF to_regclass('public.cases') IS NOT NULL THEN
    EXECUTE 'ALTER TABLE public.cases ENABLE ROW LEVEL SECURITY';

    IF NOT EXISTS (
      SELECT 1 FROM pg_policies
      WHERE schemaname = 'public' AND tablename = 'cases' AND policyname = 'cases_select_same_institution'
    ) THEN
      EXECUTE '
        CREATE POLICY cases_select_same_institution
        ON public.cases
        FOR SELECT
        TO authenticated
        USING (institution_id = public.current_institution_id())
      ';
    END IF;
  END IF;

  IF to_regclass('public.reports') IS NOT NULL THEN
    EXECUTE 'ALTER TABLE public.reports ENABLE ROW LEVEL SECURITY';

    IF NOT EXISTS (
      SELECT 1 FROM pg_policies
      WHERE schemaname = 'public' AND tablename = 'reports' AND policyname = 'reports_select_same_institution'
    ) THEN
      EXECUTE '
        CREATE POLICY reports_select_same_institution
        ON public.reports
        FOR SELECT
        TO authenticated
        USING (institution_id = public.current_institution_id())
      ';
    END IF;
  END IF;
END $$;

-- Storage policies use path convention:
-- institutions/{institution_id}/...
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'storage' AND tablename = 'objects' AND policyname = 'inputs_rw_same_institution'
  ) THEN
    EXECUTE '
      CREATE POLICY inputs_rw_same_institution
      ON storage.objects
      FOR ALL
      TO authenticated
      USING (
        bucket_id = ''neurohub-inputs''
        AND (storage.foldername(name))[1] = ''institutions''
        AND (storage.foldername(name))[2] = COALESCE((auth.jwt() ->> ''institution_id''), '''')
      )
      WITH CHECK (
        bucket_id = ''neurohub-inputs''
        AND (storage.foldername(name))[1] = ''institutions''
        AND (storage.foldername(name))[2] = COALESCE((auth.jwt() ->> ''institution_id''), '''')
      )
    ';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'storage' AND tablename = 'objects' AND policyname = 'reports_read_same_institution'
  ) THEN
    EXECUTE '
      CREATE POLICY reports_read_same_institution
      ON storage.objects
      FOR SELECT
      TO authenticated
      USING (
        bucket_id = ''neurohub-reports''
        AND (storage.foldername(name))[1] = ''institutions''
        AND (storage.foldername(name))[2] = COALESCE((auth.jwt() ->> ''institution_id''), '''')
      )
    ';
  END IF;
END $$;
