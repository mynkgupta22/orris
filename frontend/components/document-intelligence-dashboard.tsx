'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Shield, FileText, Users, Database, Eye, EyeOff, CheckCircle, AlertTriangle, Clock, Search, Brain } from 'lucide-react'

interface Document {
  id: string
  name: string
  type: 'spreadsheet' | 'document' | 'presentation' | 'pdf'
  classification: 'PI' | 'Non-PI' | 'processing'
  accessLevel: 'public' | 'restricted' | 'confidential'
  ragStatus: 'indexed' | 'processing' | 'pending'
  lastSync: Date
  userAccess: boolean
}

interface RAGQuery {
  id: string
  query: string
  status: 'processing' | 'filtering' | 'complete'
  documentsScanned: number
  accessibleDocs: number
  piFiltered: number
  response?: string
}

export default function DocumentIntelligenceDashboard() {
  const [documents, setDocuments] = useState<Document[]>([
    { id: '1', name: 'Employee Handbook 2024.docx', type: 'document', classification: 'Non-PI', accessLevel: 'public', ragStatus: 'indexed', lastSync: new Date(), userAccess: true },
    { id: '2', name: 'Salary_Report_Q3.xlsx', type: 'spreadsheet', classification: 'PI', accessLevel: 'confidential', ragStatus: 'indexed', lastSync: new Date(), userAccess: false },
    { id: '3', name: 'Company_Policies.pdf', type: 'pdf', classification: 'processing', accessLevel: 'public', ragStatus: 'processing', lastSync: new Date(), userAccess: true },
    { id: '4', name: 'Team_Directory.xlsx', type: 'spreadsheet', classification: 'PI', accessLevel: 'restricted', ragStatus: 'indexed', lastSync: new Date(), userAccess: true },
    { id: '5', name: 'Project_Roadmap.pptx', type: 'presentation', classification: 'Non-PI', accessLevel: 'public', ragStatus: 'pending', lastSync: new Date(), userAccess: true },
  ])

  const [currentQuery, setCurrentQuery] = useState<RAGQuery>({
    id: '1',
    query: 'What is our remote work policy?',
    status: 'processing',
    documentsScanned: 0,
    accessibleDocs: 0,
    piFiltered: 0
  })

  const [stats, setStats] = useState({
    totalDocs: 1247,
    piDocs: 342,
    nonPiDocs: 905,
    syncedToday: 89,
    ragQueries: 156,
    accessDenied: 23
  })

  useEffect(() => {
    const interval = setInterval(() => {
      // Simulate document processing
      setDocuments(prev => prev.map(doc => {
        if (doc.classification === 'processing') {
          return { ...doc, classification: Math.random() > 0.5 ? 'PI' : 'Non-PI' }
        }
        if (doc.ragStatus === 'processing') {
          return { ...doc, ragStatus: 'indexed' }
        }
        if (doc.ragStatus === 'pending') {
          return { ...doc, ragStatus: 'processing' }
        }
        return doc
      }))

      // Simulate RAG query processing
      setCurrentQuery(prev => {
        if (prev.status === 'processing' && prev.documentsScanned < 15) {
          return {
            ...prev,
            documentsScanned: prev.documentsScanned + Math.floor(Math.random() * 3) + 1,
            accessibleDocs: prev.accessibleDocs + Math.floor(Math.random() * 2),
            piFiltered: prev.piFiltered + Math.floor(Math.random() * 2)
          }
        } else if (prev.status === 'processing') {
          return { ...prev, status: 'filtering' }
        } else if (prev.status === 'filtering') {
          return { 
            ...prev, 
            status: 'complete',
            response: 'Based on accessible documents: Employees can work remotely up to 3 days per week with manager approval. Core hours are 10 AM - 3 PM local time.'
          }
        }
        return prev
      })

      // Update stats
      setStats(prev => ({
        ...prev,
        ragQueries: prev.ragQueries + Math.floor(Math.random() * 2),
        syncedToday: prev.syncedToday + Math.floor(Math.random() * 2)
      }))
    }, 2000)

    return () => clearInterval(interval)
  }, [])

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'spreadsheet': return '📊'
      case 'document': return '📄'
      case 'presentation': return '📊'
      case 'pdf': return '📋'
      default: return '📄'
    }
  }

  const getClassificationColor = (classification: string) => {
    switch (classification) {
      case 'PI': return 'bg-red-100 text-red-800 border-red-200'
      case 'Non-PI': return 'bg-green-100 text-green-800 border-green-200'
      case 'processing': return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      default: return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getAccessColor = (level: string) => {
    switch (level) {
      case 'public': return 'bg-blue-100 text-blue-800 border-blue-200'
      case 'restricted': return 'bg-orange-100 text-orange-800 border-orange-200'
      case 'confidential': return 'bg-purple-100 text-purple-800 border-purple-200'
      default: return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  return (
    <section className="py-20 bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 relative overflow-hidden">
      {/* Background Pattern */}
      <div className="absolute inset-0 bg-grid-slate-100 [mask-image:linear-gradient(0deg,white,rgba(255,255,255,0.6))] -z-10"></div>
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-4xl font-bold text-gray-900 mb-4">
            Live RAG Processing & Access Control
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Watch Orris sync Google Drive documents, classify PI/Non-PI data, and process RAG queries with intelligent access control in real-time
          </p>
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Stats & RAG Query Processing */}
          <div className="lg:col-span-1 space-y-6">
            {/* Stats Overview */}
            <Card className="border-0 shadow-lg bg-white/80 backdrop-blur-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg font-semibold text-gray-900 flex items-center">
                  <Database className="w-5 h-5 text-blue-600 mr-2" />
                  Google Drive Sync
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Total Documents</span>
                  <span className="text-2xl font-bold text-gray-900">{stats.totalDocs.toLocaleString()}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">PI Documents</span>
                  <span className="text-2xl font-bold text-red-600">{stats.piDocs}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Non-PI Documents</span>
                  <span className="text-2xl font-bold text-green-600">{stats.nonPiDocs}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Synced Today</span>
                  <span className="text-2xl font-bold text-blue-600">{stats.syncedToday}</span>
                </div>
              </CardContent>
            </Card>

            {/* RAG Query Processing */}
            <Card className="border-0 shadow-lg bg-white/80 backdrop-blur-sm">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg font-semibold text-gray-900 flex items-center">
                  <Brain className="w-5 h-5 text-purple-600 mr-2" />
                  Live RAG Query
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="p-3 bg-gray-50 rounded-lg">
                  <p className="text-sm font-medium text-gray-900 mb-2">"{currentQuery.query}"</p>
                  <div className="flex items-center space-x-2">
                    {currentQuery.status === 'processing' && <Clock className="w-4 h-4 text-yellow-500 animate-spin" />}
                    {currentQuery.status === 'filtering' && <Shield className="w-4 h-4 text-blue-500" />}
                    {currentQuery.status === 'complete' && <CheckCircle className="w-4 h-4 text-green-500" />}
                    <span className="text-xs text-gray-600 capitalize">{currentQuery.status}</span>
                  </div>
                </div>
                
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Documents Scanned</span>
                    <span className="font-semibold">{currentQuery.documentsScanned}/15</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Accessible to User</span>
                    <span className="font-semibold text-green-600">{currentQuery.accessibleDocs}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">PI Filtered</span>
                    <span className="font-semibold text-red-600">{currentQuery.piFiltered}</span>
                  </div>
                </div>

                {currentQuery.response && (
                  <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
                    <p className="text-sm text-green-800">{currentQuery.response}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Document Processing Feed */}
          <div className="lg:col-span-2">
            <Card className="border-0 shadow-lg bg-white/80 backdrop-blur-sm h-full">
              <CardHeader className="pb-4">
                <CardTitle className="text-lg font-semibold text-gray-900 flex items-center">
                  <FileText className="w-5 h-5 text-indigo-600 mr-2" />
                  Google Drive Documents - Live Classification
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4 max-h-96 overflow-y-auto">
                  {documents.map((doc) => (
                    <div key={doc.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-100 hover:bg-gray-100 transition-colors">
                      <div className="flex items-center space-x-4 flex-1">
                        <div className="text-2xl">{getTypeIcon(doc.type)}</div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">{doc.name}</p>
                          <div className="flex items-center space-x-2 mt-2">
                            <Badge className={`text-xs ${getClassificationColor(doc.classification)}`}>
                              {doc.classification === 'processing' ? (
                                <>
                                  <Clock className="w-3 h-3 mr-1 animate-spin" />
                                  Classifying...
                                </>
                              ) : (
                                <>
                                  {doc.classification === 'PI' ? <AlertTriangle className="w-3 h-3 mr-1" /> : <CheckCircle className="w-3 h-3 mr-1" />}
                                  {doc.classification}
                                </>
                              )}
                            </Badge>
                            <Badge className={`text-xs ${getAccessColor(doc.accessLevel)}`}>
                              {doc.accessLevel}
                            </Badge>
                            <Badge variant="outline" className="text-xs">
                              {doc.userAccess ? (
                                <>
                                  <Eye className="w-3 h-3 mr-1 text-green-600" />
                                  Accessible
                                </>
                              ) : (
                                <>
                                  <EyeOff className="w-3 h-3 mr-1 text-red-600" />
                                  Restricted
                                </>
                              )}
                            </Badge>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-4">
                        <div className="text-right">
                          {doc.ragStatus === 'processing' ? (
                            <div className="flex items-center space-x-2">
                              <Clock className="w-4 h-4 text-yellow-500 animate-spin" />
                              <span className="text-xs text-yellow-600">Indexing...</span>
                            </div>
                          ) : doc.ragStatus === 'indexed' ? (
                            <div className="flex items-center space-x-2">
                              <CheckCircle className="w-4 h-4 text-green-500" />
                              <span className="text-xs text-green-600">RAG Ready</span>
                            </div>
                          ) : (
                            <div className="flex items-center space-x-2">
                              <Clock className="w-4 h-4 text-gray-400" />
                              <span className="text-xs text-gray-500">Pending</span>
                            </div>
                          )}
                          <p className="text-xs text-gray-400 mt-1">
                            {doc.lastSync.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true }).toUpperCase()}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        <div className="mt-12 text-center">
          <p className="text-sm text-gray-500">
            Live Google Drive sync • Real-time PI classification • RAG-powered queries • Access control enforcement
          </p>
        </div>
      </div>
    </section>
  )
}
