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
      return `https://res.cloudinary.com/${this.cloudinary.cloudName}/image/upload/w_1200,q_82,f_webp/${photo.publicId}`;
    }
    // Local: thumbnail WebP gerado pelo GitHub Action em fotos/thumbs/
    const stem = photo.filename.replace(/\.[^.]+$/, '');
    return `fotos/thumbs/${stem}.webp`;
  },
};
