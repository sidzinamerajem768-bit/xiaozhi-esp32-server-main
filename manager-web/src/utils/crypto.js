/**
 * SM2 国密加密解密工具
 */

/**
 * 生成 SM2 密钥对（十六进制格式）
 */
export function generateSm2KeyPairHex() {
  const sm2 = require('sm-crypto').sm2
  const keypair = sm2.generateKeyPairHex()
  return {
    publicKey: keypair.publicKey,
    privateKey: keypair.privateKey,
    clientPublicKey: keypair.publicKey,
    clientPrivateKey: keypair.privateKey
  }
}

/**
 * SM2 公钥加密
 * @param {string} publicKey 公钥（十六进制格式）
 * @param {string} plainText 明文
 * @returns {string} 加密后的密文
 */
export function sm2Encrypt(publicKey, plainText) {
  if (!publicKey) throw new Error('公钥不能为空')
  if (!plainText) throw new Error('明文不能为空')

  const sm2 = require('sm-crypto').sm2
  const encrypted = sm2.doEncrypt(plainText, publicKey, 1)
  return '04' + encrypted
}

/**
 * SM2 私钥解密
 * @param {string} privateKey 私钥（十六进制格式）
 * @param {string} cipherText 密文（十六进制格式）
 * @returns {string} 解密后的明文
 */
export function sm2Decrypt(privateKey, cipherText) {
  const sm2 = require('sm-crypto').sm2
  const dataWithoutPrefix = cipherText.startsWith('04') ? cipherText.substring(2) : cipherText
  return sm2.doDecrypt(dataWithoutPrefix, privateKey, 1)
}