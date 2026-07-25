update storage.buckets
set allowed_mime_types = array[
  'application/epub+zip',
  'application/pdf',
  'image/jpeg',
  'application/zip'
]
where id = 'astro-knowledge-sources';
