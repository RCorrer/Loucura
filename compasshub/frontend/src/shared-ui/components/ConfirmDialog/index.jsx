import React from 'react';
import { Dialog, DialogTitle, DialogContent, DialogContentText, DialogActions, Button } from '@mui/material';

export default function ConfirmDialog({ 
  open, 
  title, 
  content, 
  onConfirm, 
  onCancel, 
  confirmText = 'Confirmar', 
  cancelText = 'Cancelar' 
}) {
  return (
    <Dialog open={open} onClose={onCancel}>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <DialogContentText>{content}</DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel}>{cancelText}</Button>
        <Button onClick={onConfirm} color="primary" variant="contained">{confirmText}</Button>
      </DialogActions>
    </Dialog>
  );
}