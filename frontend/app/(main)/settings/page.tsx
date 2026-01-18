'use client'

import { useState, useEffect, useRef } from 'react'
import { Settings, Building2, Key, Bell, Globe, Save, Eye, EyeOff, Loader2, Upload, MapPin, Plus, X, Palette, Megaphone, Target, Image, QrCode, Film, Trash2, Mail, Send, CheckCircle, XCircle } from 'lucide-react'

interface BrandAssets {
  logo?: {
    main?: string
    white?: string
    icon?: string
  }
  qrcode?: {
    wechat?: string
    wechat_official?: string
    douyin?: string
    xiaohongshu?: string
  }
  watermark?: {
    enabled?: boolean
    position?: string
    opacity?: number
    image?: string
  }
  video_assets?: {
    intro_video?: string
    outro_template?: string
  }
}

interface CompanyConfig {
  company_name: string
  company_intro: string
  contact_phone: string
  contact_email: string
  contact_wechat: string
  address: string
  advantages: string[]
  products?: Array<{ name: string; description: string; features: string[] }>
  service_routes?: Array<{ from_location: string; to_location: string; transport: string; time: string; price_ref: string }>
  faq?: Array<{ question: string; answer: string }>
  price_policy?: string
  // 新增字段
  logo_url?: string
  focus_markets?: string[]
  company_website?: string
  founded_year?: number
  employee_count?: string
  business_scope?: string
  social_media?: {
    wechat_official?: string
    douyin?: string
    xiaohongshu?: string
    video_account?: string
  }
  brand_slogan?: string
  brand_colors?: {
    primary?: string
    secondary?: string
  }
  company_values?: string[]
  content_tone?: string
  content_focus_keywords?: string[]
  forbidden_content?: string[]
  // 品牌资产
  brand_assets?: BrandAssets
}

interface ApiConfig {
  keling_access_key: string
  keling_secret_key: string
  dashscope_api_key: string
  serper_api_key: string
  pexels_api_key: string
  pixabay_api_key: string
}

interface ApiKeyStatus {
  configured: boolean
  masked_value: string
  full_value: string
}

interface NotificationConfig {
  high_intent_threshold: number
  enable_wechat_notify: boolean
  enable_email_notify: boolean
  quiet_hours_start: string
  quiet_hours_end: string
}

interface AIConfig {
  model_name: string
  temperature: number
}

interface SMTPConfig {
  smtp_host: string
  smtp_port: number
  smtp_user: string
  smtp_password: string
  sender_name: string
  email_logo?: string
}

// 资产上传组件
function AssetUploader({ 
  label, 
  description, 
  value, 
  onChange,
  small = false
}: { 
  label: string
  description: string
  value?: string
  onChange: (value: string | undefined) => void
  small?: boolean
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [error, setError] = useState(false)

  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    
    // 检查文件大小（限制2MB）
    if (file.size > 2 * 1024 * 1024) {
      alert('文件大小不能超过2MB')
      return
    }
    
    const reader = new FileReader()
    reader.onload = () => {
      setError(false)
      onChange(reader.result as string)
    }
    reader.readAsDataURL(file)
  }

  const handleDelete = () => {
    onChange(undefined)
    if (inputRef.current) {
      inputRef.current.value = ''
    }
  }

  const size = small ? 'w-24 h-24' : 'w-32 h-32'

  return (
    <div>
      <label className="block text-sm font-medium text-gray-300 mb-1">{label}</label>
      <p className="text-xs text-gray-500 mb-2">{description}</p>
      <div 
        className={`${size} bg-deep-space/50 border-2 border-dashed border-gray-600 rounded-xl flex items-center justify-center cursor-pointer hover:border-cyber-blue transition-colors overflow-hidden relative group`}
        onClick={() => inputRef.current?.click()}
      >
        {value && !error ? (
          <>
            <img 
              src={value} 
              alt={label}
              className="w-full h-full object-contain"
              onError={() => setError(true)}
            />
            <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  inputRef.current?.click()
                }}
                className="p-2 bg-cyber-blue rounded-lg hover:bg-cyber-blue/80"
              >
                <Upload className="w-4 h-4 text-white" />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  handleDelete()
                }}
                className="p-2 bg-red-500 rounded-lg hover:bg-red-600"
              >
                <Trash2 className="w-4 h-4 text-white" />
              </button>
            </div>
          </>
        ) : (
          <div className="text-center p-2">
            <Upload className={`${small ? 'w-6 h-6' : 'w-8 h-8'} text-gray-500 mx-auto mb-1`} />
            <span className="text-xs text-gray-500">点击上传</span>
          </div>
        )}
      </div>
      <input 
        ref={inputRef}
        type="file" 
        accept="image/*" 
        className="hidden" 
        onChange={handleUpload}
      />
    </div>
  )
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<'company' | 'brand' | 'content' | 'api' | 'email' | 'notification' | 'system'>('company')
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({})
  const [isSaving, setIsSaving] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const logoInputRef = useRef<HTMLInputElement>(null)
  const [logoError, setLogoError] = useState(false)

  const [companyConfig, setCompanyConfig] = useState<CompanyConfig>({
    company_name: '',
    company_intro: '',
    contact_phone: '',
    contact_email: '',
    contact_wechat: '',
    address: '',
    advantages: ['专业服务', '时效保证', '价格透明'],
    focus_markets: [],
    social_media: {},
    brand_colors: {},
    company_values: [],
    content_tone: 'professional',
    content_focus_keywords: [],
    forbidden_content: [],
    brand_assets: {
      logo: {},
      qrcode: {},
      watermark: { enabled: false, position: 'bottom-right', opacity: 0.8 },
      video_assets: {}
    }
  })

  const [apiConfig, setApiConfig] = useState<ApiConfig>({
    keling_access_key: '',
    keling_secret_key: '',
    dashscope_api_key: '',
    serper_api_key: '',
    pexels_api_key: '',
    pixabay_api_key: ''
  })
  
  const [apiKeysLoaded, setApiKeysLoaded] = useState<Record<string, ApiKeyStatus>>({})
  const [showingFullKey, setShowingFullKey] = useState<Record<string, boolean>>({})

  const [notificationConfig, setNotificationConfig] = useState<NotificationConfig>({
    high_intent_threshold: 60,
    enable_wechat_notify: true,
    enable_email_notify: false,
    quiet_hours_start: '22:00',
    quiet_hours_end: '08:00'
  })

  const [aiConfig, setAiConfig] = useState<AIConfig>({
    model_name: 'qwen-max',
    temperature: 0.7
  })

  const [smtpConfig, setSmtpConfig] = useState<SMTPConfig>({
    smtp_host: '',
    smtp_port: 465,
    smtp_user: '',
    smtp_password: '',
    sender_name: '物流智能体',
    email_logo: ''
  })
  const [smtpConfigured, setSmtpConfigured] = useState(false)
  const [testingSmtp, setTestingSmtp] = useState(false)
  const [signatureHtml, setSignatureHtml] = useState('')
  const [signatureData, setSignatureData] = useState<any>({})

  // 加载设置
  useEffect(() => {
    const fetchSettings = async () => {
      try {
        // 从公司配置API获取公司信息
        const companyRes = await fetch('/api/company/config')
        if (companyRes.ok) {
          const companyData = await companyRes.json()
          setCompanyConfig({
            company_name: companyData.company_name || '',
            company_intro: companyData.company_intro || '',
            contact_phone: companyData.contact_phone || '',
            contact_email: companyData.contact_email || '',
            contact_wechat: companyData.contact_wechat || '',
            address: companyData.address || '',
            advantages: companyData.advantages || ['专业服务', '时效保证', '价格透明'],
            products: companyData.products || [],
            service_routes: companyData.service_routes || [],
            faq: companyData.faq || [],
            price_policy: companyData.price_policy || '',
            // 新字段
            logo_url: companyData.logo_url || '',
            focus_markets: companyData.focus_markets || [],
            company_website: companyData.company_website || '',
            founded_year: companyData.founded_year || null,
            employee_count: companyData.employee_count || '',
            business_scope: companyData.business_scope || '',
            social_media: companyData.social_media || {},
            brand_slogan: companyData.brand_slogan || '',
            brand_colors: companyData.brand_colors || {},
            company_values: companyData.company_values || [],
            content_tone: companyData.content_tone || 'professional',
            content_focus_keywords: companyData.content_focus_keywords || [],
            forbidden_content: companyData.forbidden_content || [],
            brand_assets: companyData.brand_assets || {
              logo: {},
              qrcode: {},
              watermark: { enabled: false, position: 'bottom-right', opacity: 0.8 },
              video_assets: {}
            }
          })
        }
        
        // 获取通知和AI配置
        const settingsRes = await fetch('/api/settings')
        if (settingsRes.ok) {
          const data = await settingsRes.json()
          if (data.notification && Object.keys(data.notification).length > 0) {
            setNotificationConfig(prev => ({ ...prev, ...data.notification }))
          }
          if (data.ai && Object.keys(data.ai).length > 0) {
            setAiConfig(prev => ({ ...prev, ...data.ai }))
          }
        }
        
        // 获取API密钥配置
        const apiKeysRes = await fetch('/api/settings/api-keys')
        if (apiKeysRes.ok) {
          const apiKeysData = await apiKeysRes.json()
          setApiKeysLoaded(apiKeysData)
          // 将密钥值填充到apiConfig
          setApiConfig({
            keling_access_key: apiKeysData.keling_access_key?.full_value || '',
            keling_secret_key: apiKeysData.keling_secret_key?.full_value || '',
            dashscope_api_key: apiKeysData.dashscope_api_key?.full_value || '',
            serper_api_key: apiKeysData.serper_api_key?.full_value || '',
            pexels_api_key: apiKeysData.pexels_api_key?.full_value || '',
            pixabay_api_key: apiKeysData.pixabay_api_key?.full_value || ''
          })
        }
        
        // 获取SMTP配置
        const smtpRes = await fetch('/api/settings/smtp')
        if (smtpRes.ok) {
          const smtpData = await smtpRes.json()
          if (smtpData.success && smtpData.data) {
            setSmtpConfig({
              smtp_host: smtpData.data.smtp_host || '',
              smtp_port: smtpData.data.smtp_port || 465,
              smtp_user: smtpData.data.smtp_user || '',
              smtp_password: smtpData.data.smtp_password || '',
              sender_name: smtpData.data.sender_name || '物流智能体',
              email_logo: smtpData.data.email_logo || ''
            })
            setSmtpConfigured(smtpData.configured || false)
          }
        }
        
        // 获取签名预览
        const sigRes = await fetch('/api/settings/smtp/signature-preview')
        if (sigRes.ok) {
          const sigData = await sigRes.json()
          if (sigData.success) {
            setSignatureHtml(sigData.html || '')
            setSignatureData(sigData.data || {})
          }
        }
      } catch (error) {
        console.error('加载设置失败:', error)
      } finally {
        setIsLoading(false)
      }
    }

    fetchSettings()
  }, [])

  const toggleSecretVisibility = (key: string) => {
    setShowSecrets(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const handleSave = async () => {
    setIsSaving(true)
    try {
      // 保存公司设置（包括品牌和内容配置）
      if (activeTab === 'company' || activeTab === 'brand' || activeTab === 'content') {
        const res = await fetch('/api/company/config', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(companyConfig)
        })
        if (!res.ok) {
          const errorData = await res.json().catch(() => ({}))
          throw new Error(errorData.detail || `保存公司设置失败 (${res.status})`)
        }
      }
      
      // 保存通知设置
      if (activeTab === 'notification') {
        const res = await fetch('/api/settings/notification', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(notificationConfig)
        })
        if (!res.ok) {
          const errorData = await res.json().catch(() => ({}))
          throw new Error(errorData.detail || `保存通知设置失败 (${res.status})`)
        }
      }
      
      // 保存AI设置
      if (activeTab === 'system') {
        const res = await fetch('/api/settings/ai', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(aiConfig)
        })
        if (!res.ok) {
          const errorData = await res.json().catch(() => ({}))
          throw new Error(errorData.detail || `保存AI设置失败 (${res.status})`)
        }
      }
      
      // API配置保存提示
      if (activeTab === 'api') {
        alert('API密钥需要在服务器环境变量中配置，请联系管理员修改 .env 文件')
        setIsSaving(false)
        return
      }
      
      // 保存邮件配置
      if (activeTab === 'email') {
        const res = await fetch('/api/settings/smtp', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(smtpConfig)
        })
        if (!res.ok) {
          const errorData = await res.json().catch(() => ({}))
          throw new Error(errorData.detail || `保存邮件配置失败 (${res.status})`)
        }
        const data = await res.json()
        if (data.success) {
          setSmtpConfigured(true)
        }
      }
      
      alert('设置已保存！')
    } catch (error: any) {
      console.error('保存失败:', error)
      alert(`保存失败: ${error.message || '请重试'}`)
    } finally {
      setIsSaving(false)
    }
  }

  // 处理Logo上传
  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    
    // 使用 base64 编码存储 Logo
    const reader = new FileReader()
    reader.onload = () => {
      setLogoError(false)  // 重置错误状态
      setCompanyConfig(prev => ({ ...prev, logo_url: reader.result as string }))
    }
    reader.readAsDataURL(file)
  }

  // 添加标签的通用函数
  const addTag = (field: 'focus_markets' | 'advantages' | 'company_values' | 'content_focus_keywords' | 'forbidden_content', value: string) => {
    if (!value.trim()) return
    setCompanyConfig(prev => ({
      ...prev,
      [field]: [...(prev[field] || []), value.trim()]
    }))
  }

  const removeTag = (field: 'focus_markets' | 'advantages' | 'company_values' | 'content_focus_keywords' | 'forbidden_content', index: number) => {
    setCompanyConfig(prev => ({
      ...prev,
      [field]: (prev[field] || []).filter((_, i) => i !== index)
    }))
  }

  const tabs = [
    { id: 'company', label: '公司信息', icon: Building2 },
    { id: 'brand', label: '品牌设置', icon: Palette },
    { id: 'content', label: '内容配置', icon: Megaphone },
    { id: 'api', label: 'API配置', icon: Key },
    { id: 'email', label: '邮件配置', icon: Mail },
    { id: 'notification', label: '通知设置', icon: Bell },
    { id: 'system', label: '系统设置', icon: Globe }
  ]

  // 预设市场选项
  const marketOptions = [
    '德国', '荷兰', '英国', '法国', '意大利', '西班牙', '波兰', '比利时',
    '美国', '加拿大', '澳大利亚', '日本', '韩国', '新加坡', '马来西亚', '泰国'
  ]

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-cyber-blue" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Settings className="w-7 h-7 text-cyber-blue" />
            系统设置
          </h1>
          <p className="text-gray-400 mt-1">管理公司信息、品牌设置和系统配置，AI员工将从这里读取信息</p>
        </div>
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-cyber-blue to-cyber-purple rounded-lg text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          {isSaving ? '保存中...' : '保存设置'}
        </button>
      </div>

      {/* 标签页 */}
      <div className="flex gap-2 bg-dark-purple/40 rounded-xl p-1.5 overflow-x-auto">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium transition-colors whitespace-nowrap ${
              activeTab === tab.id
                ? 'bg-cyber-blue text-white'
                : 'text-gray-400 hover:text-white hover:bg-white/5'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* 公司信息 */}
      {activeTab === 'company' && (
        <div className="space-y-6">
          {/* Logo和基本信息 */}
          <div className="bg-dark-purple/40 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Building2 className="w-5 h-5 text-cyber-blue" />
              公司基本信息
            </h2>
            
            <div className="flex gap-6 mb-6">
              {/* Logo上传 */}
              <div className="flex-shrink-0">
                <label className="block text-sm font-medium text-gray-300 mb-2">公司Logo</label>
                <div 
                  className="w-32 h-32 bg-deep-space/50 border-2 border-dashed border-gray-600 rounded-xl flex items-center justify-center cursor-pointer hover:border-cyber-blue transition-colors overflow-hidden"
                  onClick={() => logoInputRef.current?.click()}
                >
                  {companyConfig.logo_url && !logoError ? (
                    <img 
                      src={companyConfig.logo_url} 
                      alt="Logo" 
                      className="w-full h-full object-contain"
                      onError={() => setLogoError(true)}
                    />
                  ) : (
                    <div className="text-center">
                      <Upload className="w-8 h-8 text-gray-500 mx-auto mb-2" />
                      <span className="text-xs text-gray-500">点击上传</span>
                    </div>
                  )}
                </div>
                <input 
                  ref={logoInputRef}
                  type="file" 
                  accept="image/*" 
                  className="hidden" 
                  onChange={handleLogoUpload}
                />
              </div>
              
              {/* 公司名称和简介 */}
              <div className="flex-1 space-y-4">
                <div className="grid grid-cols-2 gap-4">
            <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">公司名称 *</label>
              <input
                type="text"
                value={companyConfig.company_name}
                onChange={e => setCompanyConfig(prev => ({ ...prev, company_name: e.target.value }))}
                className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                placeholder="请输入公司名称"
              />
            </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">公司官网</label>
                    <input
                      type="url"
                      value={companyConfig.company_website || ''}
                      onChange={e => setCompanyConfig(prev => ({ ...prev, company_website: e.target.value }))}
                      className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                      placeholder="https://www.example.com"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">成立年份</label>
                    <input
                      type="number"
                      value={companyConfig.founded_year || ''}
                      onChange={e => setCompanyConfig(prev => ({ ...prev, founded_year: parseInt(e.target.value) || undefined }))}
                      className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                      placeholder="如：2010"
                      min={1900}
                      max={new Date().getFullYear()}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">员工规模</label>
                    <select
                      value={companyConfig.employee_count || ''}
                      onChange={e => setCompanyConfig(prev => ({ ...prev, employee_count: e.target.value }))}
                      className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                    >
                      <option value="">请选择</option>
                      <option value="1-10">1-10人</option>
                      <option value="11-50">11-50人</option>
                      <option value="51-200">51-200人</option>
                      <option value="201-500">201-500人</option>
                      <option value="500+">500人以上</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
            
            {/* 聚焦市场 - 重要！ */}
            <div className="mb-6 p-4 bg-cyber-blue/10 border border-cyber-blue/30 rounded-lg">
              <label className="block text-sm font-medium text-cyber-blue mb-2 flex items-center gap-2">
                <Target className="w-4 h-4" />
                聚焦市场 / 服务区域 *
                <span className="text-xs text-gray-400 font-normal">（AI生成内容将基于此设置）</span>
              </label>
              <div className="flex flex-wrap gap-2 mb-3">
                {(companyConfig.focus_markets || []).map((market, index) => (
                  <span
                    key={index}
                    className="px-3 py-1.5 bg-cyber-blue/20 text-cyber-blue rounded-full text-sm flex items-center gap-2"
                  >
                    <MapPin className="w-3 h-3" />
                    {market}
                    <button onClick={() => removeTag('focus_markets', index)} className="hover:text-white">
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex flex-wrap gap-2">
                {marketOptions.filter(m => !(companyConfig.focus_markets || []).includes(m)).map(market => (
                  <button
                    key={market}
                    onClick={() => addTag('focus_markets', market)}
                    className="px-3 py-1 bg-deep-space/50 border border-gray-700 rounded-full text-xs text-gray-400 hover:border-cyber-blue hover:text-cyber-blue transition-colors"
                  >
                    + {market}
                  </button>
                ))}
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">联系电话</label>
              <input
                type="text"
                value={companyConfig.contact_phone}
                onChange={e => setCompanyConfig(prev => ({ ...prev, contact_phone: e.target.value }))}
                className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                placeholder="请输入联系电话"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">联系邮箱</label>
              <input
                type="email"
                value={companyConfig.contact_email}
                onChange={e => setCompanyConfig(prev => ({ ...prev, contact_email: e.target.value }))}
                className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                placeholder="请输入联系邮箱"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">微信号</label>
              <input
                type="text"
                value={companyConfig.contact_wechat}
                onChange={e => setCompanyConfig(prev => ({ ...prev, contact_wechat: e.target.value }))}
                className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                placeholder="请输入微信号"
              />
            </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">公司地址</label>
            <input
              type="text"
              value={companyConfig.address}
              onChange={e => setCompanyConfig(prev => ({ ...prev, address: e.target.value }))}
              className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
              placeholder="请输入公司地址"
            />
              </div>
          </div>

            <div className="mt-6">
            <label className="block text-sm font-medium text-gray-300 mb-2">公司简介</label>
            <textarea
              value={companyConfig.company_intro}
              onChange={e => setCompanyConfig(prev => ({ ...prev, company_intro: e.target.value }))}
              rows={4}
              className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none resize-none"
                placeholder="请输入公司简介，AI员工将在与客户沟通、生成内容时使用这段介绍"
              />
            </div>
            
            <div className="mt-6">
              <label className="block text-sm font-medium text-gray-300 mb-2">业务范围描述</label>
              <textarea
                value={companyConfig.business_scope || ''}
                onChange={e => setCompanyConfig(prev => ({ ...prev, business_scope: e.target.value }))}
                rows={3}
                className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none resize-none"
                placeholder="详细描述公司提供的服务和业务范围，如：提供中国到欧洲的海运、空运、铁路运输服务，包含清关、FBA派送、海外仓储等"
              />
            </div>

            <div className="mt-6">
              <label className="block text-sm font-medium text-gray-300 mb-2">公司优势</label>
              <div className="flex flex-wrap gap-2">
                {companyConfig.advantages?.map((adv, index) => (
                  <span
                    key={index}
                    className="px-3 py-1.5 bg-green-500/20 text-green-400 rounded-full text-sm flex items-center gap-2"
                  >
                    {adv}
                    <button onClick={() => removeTag('advantages', index)} className="hover:text-white">
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
                <input
                  type="text"
                  placeholder="添加优势后回车..."
                  className="px-3 py-1.5 bg-deep-space/50 border border-gray-700 rounded-full text-sm text-white focus:border-cyber-blue focus:outline-none w-40"
                  onKeyDown={e => {
                    if (e.key === 'Enter' && e.currentTarget.value) {
                      addTag('advantages', e.currentTarget.value)
                      e.currentTarget.value = ''
                    }
                  }}
                />
              </div>
            </div>
          </div>

          {/* 社交媒体账号 */}
          <div className="bg-dark-purple/40 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4">社交媒体账号</h2>
            <p className="text-gray-400 text-sm mb-4">配置后，AI生成的内容将自动添加账号引流信息</p>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">微信公众号</label>
                <input
                  type="text"
                  value={companyConfig.social_media?.wechat_official || ''}
                  onChange={e => setCompanyConfig(prev => ({ 
                    ...prev, 
                    social_media: { ...prev.social_media, wechat_official: e.target.value }
                  }))}
                  className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                  placeholder="公众号ID或名称"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">抖音号</label>
                <input
                  type="text"
                  value={companyConfig.social_media?.douyin || ''}
                  onChange={e => setCompanyConfig(prev => ({ 
                    ...prev, 
                    social_media: { ...prev.social_media, douyin: e.target.value }
                  }))}
                  className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                  placeholder="抖音号"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">小红书号</label>
                <input
                  type="text"
                  value={companyConfig.social_media?.xiaohongshu || ''}
                  onChange={e => setCompanyConfig(prev => ({ 
                    ...prev, 
                    social_media: { ...prev.social_media, xiaohongshu: e.target.value }
                  }))}
                  className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                  placeholder="小红书号"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">视频号</label>
                <input
                  type="text"
                  value={companyConfig.social_media?.video_account || ''}
                  onChange={e => setCompanyConfig(prev => ({ 
                    ...prev, 
                    social_media: { ...prev.social_media, video_account: e.target.value }
                  }))}
                  className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                  placeholder="视频号"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 品牌设置 */}
      {activeTab === 'brand' && (
        <div className="space-y-6">
          {/* 品牌基本设置 */}
          <div className="bg-dark-purple/40 rounded-xl p-6 space-y-6">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Palette className="w-5 h-5 text-cyber-purple" />
              品牌基本设置
            </h2>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">品牌口号 / Slogan</label>
              <input
                type="text"
                value={companyConfig.brand_slogan || ''}
                onChange={e => setCompanyConfig(prev => ({ ...prev, brand_slogan: e.target.value }))}
                className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                placeholder="如：专注欧洲物流15年，让您的货物安全准时到达"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">企业价值观</label>
              <div className="flex flex-wrap gap-2 mb-2">
                {(companyConfig.company_values || []).map((value, index) => (
                  <span
                    key={index}
                    className="px-3 py-1.5 bg-cyber-purple/20 text-cyber-purple rounded-full text-sm flex items-center gap-2"
                  >
                    {value}
                    <button onClick={() => removeTag('company_values', index)} className="hover:text-white">
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
                <input
                  type="text"
                  placeholder="添加价值观后回车..."
                  className="px-3 py-1.5 bg-deep-space/50 border border-gray-700 rounded-full text-sm text-white focus:border-cyber-blue focus:outline-none w-40"
                  onKeyDown={e => {
                    if (e.key === 'Enter' && e.currentTarget.value) {
                      addTag('company_values', e.currentTarget.value)
                      e.currentTarget.value = ''
                    }
                  }}
                />
              </div>
              <p className="text-gray-500 text-xs">如：诚信、专业、高效、创新</p>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">品牌色</label>
              <div className="flex gap-4">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">主色调</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={companyConfig.brand_colors?.primary || '#3B82F6'}
                      onChange={e => setCompanyConfig(prev => ({ 
                        ...prev, 
                        brand_colors: { ...prev.brand_colors, primary: e.target.value }
                      }))}
                      className="w-10 h-10 rounded cursor-pointer"
                    />
                    <input
                      type="text"
                      value={companyConfig.brand_colors?.primary || '#3B82F6'}
                      onChange={e => setCompanyConfig(prev => ({ 
                        ...prev, 
                        brand_colors: { ...prev.brand_colors, primary: e.target.value }
                      }))}
                      className="w-24 px-2 py-1 bg-deep-space/50 border border-gray-700 rounded text-white text-sm"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">辅助色</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={companyConfig.brand_colors?.secondary || '#10B981'}
                      onChange={e => setCompanyConfig(prev => ({ 
                        ...prev, 
                        brand_colors: { ...prev.brand_colors, secondary: e.target.value }
                      }))}
                      className="w-10 h-10 rounded cursor-pointer"
                    />
                    <input
                      type="text"
                      value={companyConfig.brand_colors?.secondary || '#10B981'}
                      onChange={e => setCompanyConfig(prev => ({ 
                        ...prev,
                        brand_colors: { ...prev.brand_colors, secondary: e.target.value }
                      }))}
                      className="w-24 px-2 py-1 bg-deep-space/50 border border-gray-700 rounded text-white text-sm"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Logo资产 */}
          <div className="bg-dark-purple/40 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Image className="w-5 h-5 text-green-400" />
              Logo资产
              <span className="text-xs text-gray-400 font-normal ml-2">用于视频制作和内容展示</span>
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* 主Logo */}
              <AssetUploader
                label="主Logo"
                description="用于视频片头、水印等"
                value={companyConfig.brand_assets?.logo?.main}
                onChange={(value) => setCompanyConfig(prev => ({
                  ...prev,
                  brand_assets: {
                    ...prev.brand_assets,
                    logo: { ...prev.brand_assets?.logo, main: value }
                  }
                }))}
              />
              
              {/* 白色Logo */}
              <AssetUploader
                label="白色版Logo"
                description="用于深色背景"
                value={companyConfig.brand_assets?.logo?.white}
                onChange={(value) => setCompanyConfig(prev => ({
                  ...prev,
                  brand_assets: {
                    ...prev.brand_assets,
                    logo: { ...prev.brand_assets?.logo, white: value }
                  }
                }))}
              />
              
              {/* 图标版 */}
              <AssetUploader
                label="图标版"
                description="小尺寸场景使用"
                value={companyConfig.brand_assets?.logo?.icon}
                onChange={(value) => setCompanyConfig(prev => ({
                  ...prev,
                  brand_assets: {
                    ...prev.brand_assets,
                    logo: { ...prev.brand_assets?.logo, icon: value }
                  }
                }))}
              />
            </div>
          </div>

          {/* 二维码资产 */}
          <div className="bg-dark-purple/40 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <QrCode className="w-5 h-5 text-blue-400" />
              二维码资产
              <span className="text-xs text-gray-400 font-normal ml-2">视频脚本中引用的二维码图片</span>
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {/* 微信个人号 */}
              <AssetUploader
                label="微信个人号二维码"
                description="个人微信号"
                value={companyConfig.brand_assets?.qrcode?.wechat}
                onChange={(value) => setCompanyConfig(prev => ({
                  ...prev,
                  brand_assets: {
                    ...prev.brand_assets,
                    qrcode: { ...prev.brand_assets?.qrcode, wechat: value }
                  }
                }))}
              />
              
              {/* 公众号 */}
              <AssetUploader
                label="公众号二维码"
                description="微信公众号"
                value={companyConfig.brand_assets?.qrcode?.wechat_official}
                onChange={(value) => setCompanyConfig(prev => ({
                  ...prev,
                  brand_assets: {
                    ...prev.brand_assets,
                    qrcode: { ...prev.brand_assets?.qrcode, wechat_official: value }
                  }
                }))}
              />
              
              {/* 抖音 */}
              <AssetUploader
                label="抖音二维码"
                description="抖音账号"
                value={companyConfig.brand_assets?.qrcode?.douyin}
                onChange={(value) => setCompanyConfig(prev => ({
                  ...prev,
                  brand_assets: {
                    ...prev.brand_assets,
                    qrcode: { ...prev.brand_assets?.qrcode, douyin: value }
                  }
                }))}
              />
              
              {/* 小红书 */}
              <AssetUploader
                label="小红书二维码"
                description="小红书账号"
                value={companyConfig.brand_assets?.qrcode?.xiaohongshu}
                onChange={(value) => setCompanyConfig(prev => ({
                  ...prev,
                  brand_assets: {
                    ...prev.brand_assets,
                    qrcode: { ...prev.brand_assets?.qrcode, xiaohongshu: value }
                  }
                }))}
              />
            </div>
          </div>

          {/* 水印设置 */}
          <div className="bg-dark-purple/40 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Film className="w-5 h-5 text-yellow-400" />
              视频水印设置
            </h2>
            
            <div className="flex items-start gap-6">
              <div className="flex-1 space-y-4">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={companyConfig.brand_assets?.watermark?.enabled || false}
                    onChange={e => setCompanyConfig(prev => ({
                      ...prev,
                      brand_assets: {
                        ...prev.brand_assets,
                        watermark: { ...prev.brand_assets?.watermark, enabled: e.target.checked }
                      }
                    }))}
                    className="w-5 h-5 rounded bg-deep-space/50 border-gray-700 text-cyber-blue focus:ring-cyber-blue"
                  />
                  <span className="text-white">启用视频水印</span>
                </label>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-2">水印位置</label>
                    <select
                      value={companyConfig.brand_assets?.watermark?.position || 'bottom-right'}
                      onChange={e => setCompanyConfig(prev => ({
                        ...prev,
                        brand_assets: {
                          ...prev.brand_assets,
                          watermark: { ...prev.brand_assets?.watermark, position: e.target.value }
                        }
                      }))}
                      className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                    >
                      <option value="top-left">左上角</option>
                      <option value="top-right">右上角</option>
                      <option value="bottom-left">左下角</option>
                      <option value="bottom-right">右下角</option>
                      <option value="center">居中</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-2">透明度</label>
                    <input
                      type="range"
                      min="0.1"
                      max="1"
                      step="0.1"
                      value={companyConfig.brand_assets?.watermark?.opacity || 0.8}
                      onChange={e => setCompanyConfig(prev => ({
                        ...prev,
                        brand_assets: {
                          ...prev.brand_assets,
                          watermark: { ...prev.brand_assets?.watermark, opacity: parseFloat(e.target.value) }
                        }
                      }))}
                      className="w-full"
                    />
                    <div className="text-center text-gray-400 text-sm">
                      {Math.round((companyConfig.brand_assets?.watermark?.opacity || 0.8) * 100)}%
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="w-40">
                <AssetUploader
                  label="水印图片"
                  description="PNG透明背景"
                  value={companyConfig.brand_assets?.watermark?.image}
                  onChange={(value) => setCompanyConfig(prev => ({
                    ...prev,
                    brand_assets: {
                      ...prev.brand_assets,
                      watermark: { ...prev.brand_assets?.watermark, image: value }
                    }
                  }))}
                  small
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 内容配置 */}
      {activeTab === 'content' && (
        <div className="bg-dark-purple/40 rounded-xl p-6 space-y-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Megaphone className="w-5 h-5 text-yellow-400" />
            内容生成配置
          </h2>
          <p className="text-gray-400 text-sm mb-4">这些设置将影响AI自动生成的营销内容风格和方向</p>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">内容风格</label>
            <div className="flex gap-3">
              {[
                { value: 'professional', label: '专业正式', desc: '适合B2B客户' },
                { value: 'friendly', label: '亲切友好', desc: '适合中小卖家' },
                { value: 'creative', label: '创意活泼', desc: '适合社交媒体' }
              ].map(option => (
                <button
                  key={option.value}
                  onClick={() => setCompanyConfig(prev => ({ ...prev, content_tone: option.value }))}
                  className={`flex-1 p-4 rounded-lg border-2 transition-colors ${
                    companyConfig.content_tone === option.value
                      ? 'border-cyber-blue bg-cyber-blue/10'
                      : 'border-gray-700 bg-deep-space/50 hover:border-gray-600'
                  }`}
                >
                  <div className={`font-medium ${companyConfig.content_tone === option.value ? 'text-cyber-blue' : 'text-white'}`}>
                    {option.label}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">{option.desc}</div>
                </button>
              ))}
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">内容关键词</label>
            <p className="text-gray-500 text-xs mb-2">AI生成内容时会优先使用这些关键词</p>
            <div className="flex flex-wrap gap-2 mb-2">
              {(companyConfig.content_focus_keywords || []).map((keyword, index) => (
                <span
                  key={index}
                  className="px-3 py-1.5 bg-yellow-500/20 text-yellow-400 rounded-full text-sm flex items-center gap-2"
                >
                  {keyword}
                  <button onClick={() => removeTag('content_focus_keywords', index)} className="hover:text-white">
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
              <input
                type="text"
                placeholder="添加关键词后回车..."
                className="px-3 py-1.5 bg-deep-space/50 border border-gray-700 rounded-full text-sm text-white focus:border-cyber-blue focus:outline-none w-40"
                onKeyDown={e => {
                  if (e.key === 'Enter' && e.currentTarget.value) {
                    addTag('content_focus_keywords', e.currentTarget.value)
                    e.currentTarget.value = ''
                  }
                }}
              />
            </div>
            <p className="text-gray-500 text-xs">如：欧洲专线、FBA头程、DDP到门、中欧班列</p>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">禁止内容</label>
            <p className="text-gray-500 text-xs mb-2">AI生成内容时会避免出现这些词汇（如竞品名称）</p>
            <div className="flex flex-wrap gap-2 mb-2">
              {(companyConfig.forbidden_content || []).map((item, index) => (
                <span
                  key={index}
                  className="px-3 py-1.5 bg-red-500/20 text-red-400 rounded-full text-sm flex items-center gap-2"
                >
                  {item}
                  <button onClick={() => removeTag('forbidden_content', index)} className="hover:text-white">
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
              <input
                type="text"
                placeholder="添加禁用词后回车..."
                className="px-3 py-1.5 bg-deep-space/50 border border-gray-700 rounded-full text-sm text-white focus:border-cyber-blue focus:outline-none w-40"
                onKeyDown={e => {
                  if (e.key === 'Enter' && e.currentTarget.value) {
                    addTag('forbidden_content', e.currentTarget.value)
                    e.currentTarget.value = ''
                  }
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* API配置 */}
      {activeTab === 'api' && (
        <div className="bg-dark-purple/40 rounded-xl p-6 space-y-6">
          <h2 className="text-lg font-semibold text-white mb-4">API密钥配置</h2>
          <div className="p-4 bg-blue-400/10 border border-blue-400/30 rounded-lg text-blue-400 text-sm mb-6">
            ℹ️ 以下是服务器已配置的API密钥。如需修改请联系管理员更新服务器 .env 文件。
          </div>

          <div className="grid gap-6">
            {[
              { key: 'dashscope_api_key', label: '通义千问 API Key', desc: '用于AI对话和文案生成', icon: '🤖' },
              { key: 'keling_access_key', label: '可灵AI Access Key', desc: '用于AI视频生成', icon: '🎬' },
              { key: 'keling_secret_key', label: '可灵AI Secret Key', desc: '用于AI视频生成', icon: '🔐' },
              { key: 'serper_api_key', label: 'Serper API Key', desc: '用于线索搜索', icon: '🔍' },
              { key: 'pexels_api_key', label: 'Pexels API Key', desc: '用于素材采集', icon: '📷' },
              { key: 'pixabay_api_key', label: 'Pixabay API Key', desc: '用于素材采集', icon: '🖼️' }
            ].map(item => {
              const keyStatus = apiKeysLoaded[item.key]
              const isConfigured = keyStatus?.configured
              const displayValue = showSecrets[item.key] 
                ? (keyStatus?.full_value || '') 
                : (keyStatus?.masked_value || '')
              
              return (
                <div key={item.key} className="p-4 bg-deep-space/30 rounded-lg border border-gray-700/50">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xl">{item.icon}</span>
                        <label className="text-sm font-medium text-white">{item.label}</label>
                        {isConfigured ? (
                          <span className="px-2 py-0.5 text-xs bg-green-500/20 text-green-400 rounded-full">✓ 已配置</span>
                        ) : (
                          <span className="px-2 py-0.5 text-xs bg-red-500/20 text-red-400 rounded-full">✗ 未配置</span>
                        )}
                      </div>
                      <p className="text-gray-500 text-xs mb-3">{item.desc}</p>
                      
                      <div className="relative">
                        <input
                          type="text"
                          value={displayValue}
                          readOnly
                          className={`w-full px-4 py-2.5 bg-deep-space/50 border rounded-lg text-white pr-12 font-mono text-sm ${
                            isConfigured ? 'border-green-500/30' : 'border-gray-700'
                          }`}
                          placeholder={isConfigured ? '密钥已配置' : '未配置'}
                        />
                        {isConfigured && (
                          <button
                            type="button"
                            onClick={() => setShowSecrets(prev => ({ ...prev, [item.key]: !prev[item.key] }))}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white transition-colors"
                            title={showSecrets[item.key] ? '隐藏密钥' : '显示完整密钥'}
                          >
                            {showSecrets[item.key] ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
          
          {/* 统计信息 */}
          <div className="mt-6 p-4 bg-deep-space/30 rounded-lg border border-gray-700/50">
            <h3 className="text-sm font-medium text-gray-300 mb-3">配置状态汇总</h3>
            <div className="flex gap-4">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 bg-green-500 rounded-full"></span>
                <span className="text-sm text-gray-400">
                  已配置: {Object.values(apiKeysLoaded).filter(k => k?.configured).length} 个
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 bg-red-500 rounded-full"></span>
                <span className="text-sm text-gray-400">
                  未配置: {6 - Object.values(apiKeysLoaded).filter(k => k?.configured).length} 个
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 邮件配置 */}
      {activeTab === 'email' && (
        <div className="space-y-6">
          {/* 配置状态提示 */}
          <div className={`p-4 rounded-lg border ${smtpConfigured 
            ? 'bg-green-500/10 border-green-500/30' 
            : 'bg-yellow-500/10 border-yellow-500/30'
          }`}>
            <div className="flex items-center gap-3">
              {smtpConfigured ? (
                <>
                  <CheckCircle className="w-5 h-5 text-green-400" />
                  <span className="text-green-400">SMTP已配置，邮件功能可用</span>
                </>
              ) : (
                <>
                  <XCircle className="w-5 h-5 text-yellow-400" />
                  <span className="text-yellow-400">SMTP未配置，请填写以下信息以启用邮件跟进功能</span>
                </>
              )}
            </div>
          </div>

          {/* SMTP配置表单 */}
          <div className="bg-dark-purple/40 rounded-xl p-6 space-y-6">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Mail className="w-5 h-5 text-cyber-blue" />
              SMTP邮件服务配置
            </h2>
            <p className="text-gray-400 text-sm">
              配置SMTP服务后，AI员工（小跟）可以通过邮件跟进客户
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">SMTP服务器地址 *</label>
                <input
                  type="text"
                  value={smtpConfig.smtp_host}
                  onChange={e => setSmtpConfig(prev => ({ ...prev, smtp_host: e.target.value }))}
                  className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                  placeholder="如：smtp.qq.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">端口号 *</label>
                <input
                  type="number"
                  value={smtpConfig.smtp_port}
                  onChange={e => setSmtpConfig(prev => ({ ...prev, smtp_port: parseInt(e.target.value) || 465 }))}
                  className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                  placeholder="465"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">发件邮箱 *</label>
                <input
                  type="email"
                  value={smtpConfig.smtp_user}
                  onChange={e => setSmtpConfig(prev => ({ ...prev, smtp_user: e.target.value }))}
                  className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                  placeholder="your-email@qq.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  授权码/密码 *
                  <span className="text-gray-500 text-xs ml-2">（QQ邮箱请使用授权码）</span>
                </label>
                <input
                  type="password"
                  value={smtpConfig.smtp_password}
                  onChange={e => setSmtpConfig(prev => ({ ...prev, smtp_password: e.target.value }))}
                  className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                  placeholder="输入授权码或密码"
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-300 mb-2">发件人名称</label>
                <input
                  type="text"
                  value={smtpConfig.sender_name}
                  onChange={e => setSmtpConfig(prev => ({ ...prev, sender_name: e.target.value }))}
                  className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                  placeholder="物流智能体"
                />
                <p className="text-gray-500 text-xs mt-1">收件人看到的发件人名称</p>
              </div>
            </div>

            {/* 邮件Logo上传 */}
            <div className="pt-4 border-t border-gray-700">
              <h3 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
                <Image className="w-4 h-4" />
                邮件专用Logo
                <span className="text-xs text-gray-500 font-normal">（显示在邮件签名顶部）</span>
              </h3>
              <div className="flex items-start gap-4">
                {smtpConfig.email_logo ? (
                  <div className="relative">
                    <img 
                      src={smtpConfig.email_logo} 
                      alt="邮件Logo" 
                      className="h-16 w-auto object-contain bg-white rounded-lg p-2"
                    />
                    <button
                      onClick={() => setSmtpConfig(prev => ({ ...prev, email_logo: '' }))}
                      className="absolute -top-2 -right-2 p-1 bg-red-500 rounded-full text-white hover:bg-red-600"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ) : (
                  <label className="flex flex-col items-center justify-center w-32 h-16 border-2 border-dashed border-gray-600 rounded-lg cursor-pointer hover:border-cyber-blue/50 transition-colors">
                    <Upload className="w-5 h-5 text-gray-500" />
                    <span className="text-xs text-gray-500 mt-1">上传Logo</span>
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0]
                        if (file) {
                          if (file.size > 500 * 1024) {
                            alert('Logo文件大小不能超过500KB')
                            return
                          }
                          const reader = new FileReader()
                          reader.onload = () => {
                            setSmtpConfig(prev => ({ ...prev, email_logo: reader.result as string }))
                          }
                          reader.readAsDataURL(file)
                        }
                      }}
                    />
                  </label>
                )}
                <p className="text-gray-500 text-xs">
                  建议尺寸：宽度150-200px，PNG/JPG格式，支持透明背景<br/>
                  此Logo与公司信息中的Logo不同，仅用于邮件签名
                </p>
              </div>
            </div>

            {/* 测试按钮 */}
            <div className="flex items-center gap-4 pt-4 border-t border-gray-700">
              <button
                onClick={async () => {
                  // 先保存配置
                  setTestingSmtp(true)
                  try {
                    // 保存
                    await fetch('/api/settings/smtp', {
                      method: 'PUT',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify(smtpConfig)
                    })
                    
                    // 测试
                    const res = await fetch('/api/settings/smtp/test', { method: 'POST' })
                    const data = await res.json()
                    
                    if (data.success) {
                      alert(`✅ ${data.message}`)
                      setSmtpConfigured(true)
                    } else {
                      alert(`❌ 测试失败: ${data.message}`)
                    }
                  } catch (error) {
                    alert('测试失败，请检查配置')
                  } finally {
                    setTestingSmtp(false)
                  }
                }}
                disabled={testingSmtp || !smtpConfig.smtp_host || !smtpConfig.smtp_user}
                className="flex items-center gap-2 px-4 py-2 bg-cyber-blue/20 border border-cyber-blue/50 rounded-lg text-cyber-blue hover:bg-cyber-blue/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {testingSmtp ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    测试中...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    发送测试邮件
                  </>
                )}
              </button>
              <span className="text-gray-500 text-sm">
                测试邮件将发送到配置的发件邮箱
              </span>
            </div>
          </div>

          {/* 邮件签名预览 */}
          <div className="bg-dark-purple/40 rounded-xl p-6">
            <h3 className="text-sm font-medium text-gray-300 mb-4 flex items-center gap-2">
              ✍️ 邮件签名预览
              <span className="text-xs text-gray-500 font-normal">（签名内容从"公司信息"读取）</span>
            </h3>
            
            {signatureHtml ? (
              <div className="bg-white rounded-lg p-4 text-gray-800">
                <div dangerouslySetInnerHTML={{ __html: signatureHtml }} />
              </div>
            ) : (
              <div className="bg-deep-space/30 rounded-lg p-4 text-gray-500 text-center">
                <p>暂无签名内容</p>
                <p className="text-xs mt-1">请先在"公司信息"中填写联系方式</p>
              </div>
            )}
            
            {/* 签名内容来源说明 */}
            <div className="mt-4 p-3 bg-deep-space/30 rounded-lg text-xs text-gray-500">
              <p className="font-medium text-gray-400 mb-2">签名读取的字段：</p>
              <div className="grid grid-cols-2 gap-2">
                <div className="flex items-center gap-2">
                  <span className={signatureData.email_logo ? 'text-green-400' : 'text-gray-600'}>
                    {signatureData.email_logo ? '✓' : '○'}
                  </span>
                  邮件Logo: {signatureData.email_logo ? '已上传' : '未设置（本页上传）'}
                </div>
                <div className="flex items-center gap-2">
                  <span className={signatureData.sender_name ? 'text-green-400' : 'text-gray-600'}>
                    {signatureData.sender_name ? '✓' : '○'}
                  </span>
                  发件人名称: {signatureData.sender_name || '未设置'}
                </div>
                <div className="flex items-center gap-2">
                  <span className={signatureData.company_name ? 'text-green-400' : 'text-gray-600'}>
                    {signatureData.company_name ? '✓' : '○'}
                  </span>
                  公司名称: {signatureData.company_name || '未设置'}
                </div>
                <div className="flex items-center gap-2">
                  <span className={signatureData.address ? 'text-green-400' : 'text-gray-600'}>
                    {signatureData.address ? '✓' : '○'}
                  </span>
                  地址: {signatureData.address || '未设置'}
                </div>
                <div className="flex items-center gap-2">
                  <span className={signatureData.contact_phone ? 'text-green-400' : 'text-gray-600'}>
                    {signatureData.contact_phone ? '✓' : '○'}
                  </span>
                  联系电话: {signatureData.contact_phone || '未设置'}
                </div>
                <div className="flex items-center gap-2">
                  <span className={signatureData.contact_email ? 'text-green-400' : 'text-gray-600'}>
                    {signatureData.contact_email ? '✓' : '○'}
                  </span>
                  联系邮箱: {signatureData.contact_email || '未设置'}
                </div>
                <div className="flex items-center gap-2">
                  <span className={signatureData.contact_wechat ? 'text-green-400' : 'text-gray-600'}>
                    {signatureData.contact_wechat ? '✓' : '○'}
                  </span>
                  微信号: {signatureData.contact_wechat || '未设置'}
                </div>
                <div className="flex items-center gap-2">
                  <span className={signatureData.wechat_qrcode ? 'text-green-400' : 'text-gray-600'}>
                    {signatureData.wechat_qrcode ? '✓' : '○'}
                  </span>
                  微信二维码: {signatureData.wechat_qrcode ? '已上传' : '未设置（品牌资产上传）'}
                </div>
                <div className="flex items-center gap-2">
                  <span className={signatureData.company_website ? 'text-green-400' : 'text-gray-600'}>
                    {signatureData.company_website ? '✓' : '○'}
                  </span>
                  官网: {signatureData.company_website || '未设置'}
                </div>
              </div>
              <p className="mt-3 text-gray-500">
                💡 如需修改签名内容，请前往 <a href="/settings" onClick={() => setActiveTab('company')} className="text-cyber-blue hover:underline">公司信息</a> 页面更新
              </p>
            </div>
          </div>

          {/* 常用邮箱配置参考 */}
          <div className="bg-dark-purple/40 rounded-xl p-6">
            <h3 className="text-sm font-medium text-gray-300 mb-4">常用邮箱SMTP配置参考</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div className="p-3 bg-deep-space/30 rounded-lg">
                <div className="font-medium text-white mb-2">QQ邮箱</div>
                <div className="text-gray-400 space-y-1">
                  <p>服务器: smtp.qq.com</p>
                  <p>端口: 465 (SSL)</p>
                  <p className="text-yellow-400 text-xs">需要开启SMTP并获取授权码</p>
                </div>
              </div>
              <div className="p-3 bg-deep-space/30 rounded-lg">
                <div className="font-medium text-white mb-2">阿里云企业邮箱</div>
                <div className="text-gray-400 space-y-1">
                  <p>服务器: smtp.mxhichina.com</p>
                  <p>端口: 465 (SSL)</p>
                </div>
              </div>
              <div className="p-3 bg-deep-space/30 rounded-lg">
                <div className="font-medium text-white mb-2">163邮箱</div>
                <div className="text-gray-400 space-y-1">
                  <p>服务器: smtp.163.com</p>
                  <p>端口: 465 (SSL)</p>
                  <p className="text-yellow-400 text-xs">需要开启SMTP并获取授权码</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 通知设置 */}
      {activeTab === 'notification' && (
        <div className="bg-dark-purple/40 rounded-xl p-6 space-y-6">
          <h2 className="text-lg font-semibold text-white mb-4">通知设置</h2>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              高意向客户通知阈值
            </label>
            <p className="text-gray-500 text-xs mb-2">
              当客户意向分数达到此阈值时，系统将发送通知提醒
            </p>
            <input
              type="number"
              value={notificationConfig.high_intent_threshold}
              onChange={e => setNotificationConfig(prev => ({ ...prev, high_intent_threshold: parseInt(e.target.value) }))}
              className="w-32 px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
              min={0}
              max={100}
            />
            <span className="text-gray-400 ml-2">分</span>
          </div>

          <div className="space-y-4">
            <h3 className="text-sm font-medium text-gray-300">通知方式</h3>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={notificationConfig.enable_wechat_notify}
                onChange={e => setNotificationConfig(prev => ({ ...prev, enable_wechat_notify: e.target.checked }))}
                className="w-5 h-5 rounded bg-deep-space/50 border-gray-700 text-cyber-blue focus:ring-cyber-blue"
              />
              <span className="text-white">微信通知</span>
            </label>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={notificationConfig.enable_email_notify}
                onChange={e => setNotificationConfig(prev => ({ ...prev, enable_email_notify: e.target.checked }))}
                className="w-5 h-5 rounded bg-deep-space/50 border-gray-700 text-cyber-blue focus:ring-cyber-blue"
              />
              <span className="text-white">邮件通知</span>
            </label>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-300 mb-2">免打扰时段</h3>
            <div className="flex items-center gap-4">
              <input
                type="time"
                value={notificationConfig.quiet_hours_start}
                onChange={e => setNotificationConfig(prev => ({ ...prev, quiet_hours_start: e.target.value }))}
                className="px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
              />
              <span className="text-gray-400">至</span>
              <input
                type="time"
                value={notificationConfig.quiet_hours_end}
                onChange={e => setNotificationConfig(prev => ({ ...prev, quiet_hours_end: e.target.value }))}
                className="px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
              />
            </div>
          </div>
        </div>
      )}

      {/* 系统设置 */}
      {activeTab === 'system' && (
        <div className="bg-dark-purple/40 rounded-xl p-6 space-y-6">
          <h2 className="text-lg font-semibold text-white mb-4">系统设置</h2>

          <div>
            <h3 className="text-sm font-medium text-gray-300 mb-4">默认语言</h3>
            <select className="px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none">
              <option value="zh-CN">中文 (简体)</option>
              <option value="en-US">English (US)</option>
            </select>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-300 mb-4">AI模型配置</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-gray-500 mb-1">主模型</label>
                <select 
                  value={aiConfig.model_name}
                  onChange={e => setAiConfig(prev => ({ ...prev, model_name: e.target.value }))}
                  className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                >
                  <option value="qwen-max">通义千问 Max</option>
                  <option value="qwen-plus">通义千问 Plus</option>
                  <option value="qwen-turbo">通义千问 Turbo</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">创造性参数 (0-1)</label>
                <input
                  type="number"
                  value={aiConfig.temperature}
                  onChange={e => setAiConfig(prev => ({ ...prev, temperature: parseFloat(e.target.value) }))}
                  step={0.1}
                  min={0}
                  max={1}
                  className="w-full px-4 py-2.5 bg-deep-space/50 border border-gray-700 rounded-lg text-white focus:border-cyber-blue focus:outline-none"
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
