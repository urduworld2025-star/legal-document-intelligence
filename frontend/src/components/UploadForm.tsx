import { ChangeEvent, FormEvent, useState } from "react";
import styles from "./UploadForm.module.css";

export type SubmitAction = "parse" | "extract" | "classify";

interface UploadFormProps {
  disabled: boolean;
  onSubmit: (file: File, action: SubmitAction) => void;
  canAnalyze?: boolean;
}

export function UploadForm({ disabled, onSubmit, canAnalyze = true }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const blocked = disabled || !canAnalyze;

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
  }

  function submit(event: FormEvent, action: SubmitAction) {
    event.preventDefault();
    if (!file) return;
    onSubmit(file, action);
  }

  return (
    <form className={styles.form}>
      {!canAnalyze && (
        <p className={styles.note}>Your role doesn't include document analysis — this form is view-only.</p>
      )}
      <label className={styles.field}>
        <span>Contract file (.pdf or .docx)</span>
        <input type="file" accept=".pdf,.docx" onChange={handleFileChange} disabled={blocked} />
      </label>

      <div className={styles.actions}>
        <button type="button" disabled={blocked || !file} onClick={(e) => submit(e, "parse")}>
          Parse Document
        </button>
        <button type="button" disabled={blocked || !file} onClick={(e) => submit(e, "extract")}>
          Extract Clauses
        </button>
        <button type="button" disabled={blocked || !file} onClick={(e) => submit(e, "classify")}>
          Classify Document
        </button>
      </div>
    </form>
  );
}
