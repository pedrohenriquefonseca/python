/**
 * Camada de abstração de armazenamento.
 *
 * Para migrar para Cloudinary no futuro:
 *   1. Altere storage para 'cloudinary'
 *   2. Preencha cloudinary.cloudName
 *   3. O campo publicId de cada entrada em fotos.json deve ser
 *      preenchido pelo script de processamento (process_photos.py)
 */
const Config = {
  storage: 'local', // 'local' | 'cloudinary'

  cloudinary: {
    cloudName: '', // ex: 'pedro-fonseca-foto'
  },

  getImageUrl(photo) {
    if (this.storage === 'cloudinary') {
      return `https://res.cloudinary.com/${this.cloudinary.cloudName}/image/upload/${photo.publicId}`;
    }
    return `fotos/${photo.filename}`;
  },

  getThumbnailUrl(photo) {
    if (this.storage === 'cloudinary') {
      // Cloudinary redimensiona e otimiza automaticamente
      return `https://res.cloudinary.com/${this.cloudinary.cloudName}/image/upload/w_800,q_auto,f_auto/${photo.publicId}`;
    }
    // Local: usa o arquivo original (sem geração de thumbnail)
    return `fotos/${photo.filename}`;
  },
};
