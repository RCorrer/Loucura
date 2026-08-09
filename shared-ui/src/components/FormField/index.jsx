import React from 'react';
import { TextField, FormControl, FormHelperText } from '@mui/material';

export default function FormField({
  label,
  value,
  onChange,
  error,
  helperText,
  type = 'text',
  required = false,
  fullWidth = true,
  ...props
}) {
  return (
    <FormControl fullWidth={fullWidth} error={!!error}>
      <TextField
        label={label}
        value={value}
        onChange={onChange}
        type={type}
        required={required}
        error={!!error}
        helperText={helperText}
        {...props}
      />
    </FormControl>
  );
}