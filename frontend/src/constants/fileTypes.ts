/** Keep in sync with backend app/services/file_types.py */

export const TEXT_FILE_EXTENSIONS = ['.pdf', '.docx', '.md', '.txt', '.xlsx', '.xls'] as const;

export const IMAGE_FILE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp'] as const;

export const ALLOWED_FILE_EXTENSIONS = [
  ...TEXT_FILE_EXTENSIONS,
  ...IMAGE_FILE_EXTENSIONS,
] as const;

export const FILE_ACCEPT_ATTR = [
  ...ALLOWED_FILE_EXTENSIONS,
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'application/vnd.ms-excel',
  'image/png',
  'image/jpeg',
  'image/webp',
  'image/gif',
  'image/bmp',
].join(',');

export function isAllowedUploadFile(file: File): boolean {
  const name = file.name.toLowerCase();
  return ALLOWED_FILE_EXTENSIONS.some((ext) => name.endsWith(ext));
}

export function isImageFileType(fileType: string): boolean {
  return ['png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp'].includes(fileType.toLowerCase());
}
