"""

  This code is released under the GNU Affero General Public License.
  
  OpenEnergyMonitor project:
  http://openenergymonitor.org

"""

"""class AbstractBuffer

Represents the actual buffer being used.
"""
class AbstractBuffer():
  def storeItem(self,data): pass
  def retrieveItem(self): pass
  def removeLastRetrievedItem(self): pass
  def size(self): pass

"""
This implementation of the AbstractBuffer just uses an in-memory datastructure.
It's basically identical to the previous (inline) buffer.
"""
class InMemoryBuffer(AbstractBuffer):
  maximumEntriesInBuffer = 1000
  
  def __init__(self):
    self._data_buffer = []
    
  def isFull(self):
    return self.size() >= InMemoryBuffer.maximumEntriesInBuffer

  def discardOldestItem(self):
    self._data_buffer = self._data_buffer[size - InMemoryBuffer.maximumEntriesInBuffer:]
      
  def discardOldestItemIfFull(self):
    if self.isFull():
      self.discardOldestItem()
        
  def storeItem(self,data):
    self.discardOldestItemIfFull();
            
    self._data_buffer.append (data)
    
  def retrieveItem(self):
    return self._data_buffer[0]
    
  def removeLastRetrievedItem(self):
    del self._data_buffer[0]
    
  def size(self):
    return len(self._data_buffer)