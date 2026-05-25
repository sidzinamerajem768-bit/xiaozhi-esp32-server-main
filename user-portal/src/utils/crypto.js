import { sm2 } from 'sm-crypto'

export function sm2Encrypt(publicKey, plainText) {
  if (!publicKey) throw new Error('公钥不能为空')
  if (!plainText) throw new Error('明文不能为空')
  const encrypted = sm2.doEncrypt(plainText, publicKey, 1)
  return '04' + encrypted
}
