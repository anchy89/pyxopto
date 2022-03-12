# -*- coding: utf-8 -*-
################################ Begin license #################################
# Copyright (C) Laboratory of Imaging technologies,
#               Faculty of Electrical Engineering,
#               University of Ljubljana.
#
# This file is part of PyXOpto.
#
# PyXOpto is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyXOpto is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PyXOpto. If not, see <https://www.gnu.org/licenses/>.
################################# End license ##################################

from typing import Dict, List, Tuple

import numpy as np
from xopto.mcbase import cltypes
from xopto.mcbase import mctypes
from xopto.mcbase import mcoptions
from xopto.mcbase import mcobject
from xopto.mcbase.mcutil.axis import Axis


class Fluencet(mcobject.McObject):
    @staticmethod
    def cl_type(mc: mcobject.McObject) -> cltypes.Structure:
        T = mc.types
        class ClFluencet(cltypes.Structure):
            '''
            OpenCL structure that used by the Monte carlo simulator.

            Fields
            ------
            inv_step: McTypes.cl_point4f
                Inverse spacings of the fluence accumulators.
            top_left: McTypes.cl_point4f
                Coordinates of the top-left corner of the fluence accumulators.
            shape: McTypes.cl_point4
                Shape/size of the accumulator along the x, y, z and
                temporal axis.
            offset: McTypes.mc_int_t
                Offset of the first element of the fluence accumulator buffer.
            k: McTypes.cl_float
                Integer factor that converts floating point photon packet
                weight to integer value compatible with the fluence
                accumulators.
            '''
            _fields_ = [
                ('inv_step', T.mc_point4f_t),
                ('top_left', T.mc_point4f_t),
                ('shape', T.mc_point4_t),
                ('offset', T.mc_size_t),
                ('k', T.mc_int_t),
            ]

        return ClFluencet

    @staticmethod
    def cl_declaration(mc: mcobject.McObject) -> str:
        return '\n'.join((
            'struct MC_STRUCT_ATTRIBUTES McFluence{',
            '	mc_point4f_t inv_step;',
            '	mc_point4f_t top_left;',
            '	mc_point4_t shape;',
            '	mc_size_t offset;',
            '	mc_int_t k;',
            '};',
        ))

    @staticmethod
    def cl_implementation(mc: mcobject.McObject):
        return '\n'.join((
            'void dbg_print_fluence(__mc_fluence_mem const McFluence *fluence){',
            '	dbg_print("Chartesian time-resolved McFluence fluence:");',
            '	dbg_print_float(INDENT "top_left.x (mm):", fluence->top_left.x*1e3f);',
            '	dbg_print_float(INDENT "top_left.y (mm):", fluence->top_left.y*1e3f);',
            '	dbg_print_float(INDENT "top_left.z (mm):", fluence->top_left.z*1e3f);',
            '	dbg_print_float(INDENT "top_left.w (ns):",  fluence->top_left.w*1e9f);',
            '	dbg_print_float(INDENT "inv_step.x (1/mm):", fluence->inv_step.x*1e-3f);',
            '	dbg_print_float(INDENT "inv_step.y (1/mm):", fluence->inv_step.y*1e-3f);',
            '	dbg_print_float(INDENT "inv_step.z (1/mm):", fluence->inv_step.z*1e-3f);',
            '	dbg_print_float(INDENT "inv_step.w (1/ns):", fluence->inv_step.w*1e-9f);',
            '	dbg_print_int(INDENT "shape.x:", fluence->shape.x);',
            '	dbg_print_int(INDENT "shape.y:", fluence->shape.y);',
            '	dbg_print_int(INDENT "shape.z:", fluence->shape.z);',
            '	dbg_print_int(INDENT "shape.w:", fluence->shape.w);',
            '	dbg_print_size_t(INDENT "offset:", fluence->offset);',
            '	dbg_print_int(INDENT "k:", fluence->k);',
            '',
            '	#if MC_FLUENCE_MODE_RATE',
            '		dbg_print(INDENT "Mode: fluence");',
            '	#else',
            '		dbg_print(INDENT "Mode: deposition");',
            '	#endif',
            '};',
            '',
            '#if MC_FLUENCE_MODE_RATE',
            'inline void mcsim_fluence_deposit_at(',
            '	McSim *mcsim, mc_point3f_t const *position, ',
            '	mc_fp_t weight, mc_fp_t mua){',
            '#else',
            'inline void mcsim_fluence_deposit_at(',
            '	McSim *mcsim, mc_point3f_t const *position, mc_fp_t weight){',
            '#endif',
            '	mc_fp_t indexf_x, indexf_y, indexf_z, indexf_t;',
            '	__mc_fluence_mem McFluence const *fluence = mcsim_fluence(mcsim);',
            '',
            '	indexf_x = (position->x - fluence->top_left.x)*',
            '		fluence->inv_step.x;',
            '	indexf_y = (position->y - fluence->top_left.y)*',
            '		fluence->inv_step.y;',
            '	indexf_z = (position->z - fluence->top_left.z)*',
            '		fluence->inv_step.z;',
            '	indexf_t = (mcsim_optical_pathlength(mcsim)*FP_INV_C - ',
            '		fluence->top_left.w)*fluence->inv_step.w;',
            '',
            '	if (indexf_t >= FP_0 && indexf_x >= FP_0 && ',
            '			indexf_y >= FP_0 && indexf_z >= FP_0 &&',
            '			indexf_x < fluence->shape.x && ',
            '			indexf_y < fluence->shape.y && '
            '			indexf_z < fluence->shape.z && ',
            '			indexf_t < fluence->shape.w) {',
            '		mc_size_t index, index_x, index_y, index_z, index_t;',
            '',
            '		index_x = mc_uint(indexf_x);',
            '		index_y = mc_uint(indexf_y);',
            '		index_z = mc_uint(indexf_z);',
            '		index_t = mc_uint(indexf_t);',
            '		index = ((index_z*fluence->shape.y + index_y)*fluence->shape.x + index_x)*fluence->shape.w + index_t;',
            '		#if MC_ENABLE_DEBUG',
            '		mc_point4_t index_xyz = {index_x, index_y, index_z, index_t};',
            '		dbg_print("Fluence depositing:");',
            '		dbg_print_float(INDENT     "weight                    :", weight);',
            '		dbg_print_point4(INDENT    "voxel address (x, y, z, t):", &index_xyzt);',
            '		dbg_print_int(INDENT       "flat index                :", index);',
            '		dbg_print_size_t(INDENT    "offset                    :", fluence->offset);',
            '		#endif',
            '',
            '		#if MC_FLUENCE_MODE_RATE',
            '		weight *= (mua != FP_0) ? mc_fdiv(FP_1, mua) : FP_0;',
            '		#endif'
            '',
            '		__global uint32_t *address = ',
            '			(__global void *)(mcsim_accumulator_buffer_ex(mcsim, fluence->offset + index));',
            '		uint32_t ui32w = (uint32_t)(weight*fluence->k + FP_0p5);',
            '',
            '		accumulator_deposit(address, ui32w);',
            '	};',
            '};',
        ))

    '''
    Maximum integer '0x7FFFFF' (8388607) that can be represented by a floating
    point number is used by default to convert photon packet weight
    (floating point) to accumulator data type (unsigned integer).
    '''

    def cl_options(self, mc: mcobject.McObject) -> mcoptions.RawOptions:
        return [('MC_USE_FLUENCE', True),
                ('MC_FLUENCE_MODE_RATE', self.mode == 'fluence'),
                ('MC_TRACK_OPTICAL_PATHLENGTH', True)]

    def __init__(self, xaxis: Axis or 'Fluencet', yaxis: Axis = None,
                 zaxis: Axis = None, taxis: Axis = None,
                 mode: str = 'deposition'):
        '''
        Fluence object constructor. Default constructor disables the
        fluence functionality by creating a zero-size fluence accumulator array.

        Parameters
        ----------
        xaxis: Axis or Fluencet
            Axis that defines accumulators along the x axis.
            If Fluencet instance, a new copy is created.
        yaxis: Axis
            Axis that defines accumulators along the y axis.
        zaxis: Axis
            Axis that defines accumulators along the z axis.
        taxis: Axis
            Axis that defines accumulators along the temporal axis.
        mode: str from ('deposition', 'fluence')
            Mode that is used to accumulate the photon packet weight:

            - fluence - fluence rate ( 1/m :superscript:`2`)
            - deposition - absorbed energy (sum of photon packet weights
              absorbed in the voxel 1/m :superscript:`3`).

        Note
        ----
            The fluence accumulator buffer data type is inherited from the
            Monte Carlo simulator mc_accu_t type.
        '''
        data = None
        nphotons = 0
        k = mctypes.McFloat32.mc_fp_maxint

        if isinstance(xaxis, Fluencet):
            fluence = xaxis
            xaxis = Axis(fluence.xaxis)
            yaxis = Axis(fluence.yaxis)
            zaxis = Axis(fluence.zaxis)
            taxis = Axis(fluence.taxis)
            nphotons = fluence.nphotons
            mode = fluence.mode
            k = fluence.k

            if fluence.raw is not None:
                data = np.copy(fluence.raw)

        if mode not in ('fluence', 'deposition'):
            raise ValueError(
                'The value of mode parameter must be '
                '"fluence" or "deposition" but got {}!'.format(mode))

        if xaxis is None:
            xaxis = Axis(-0.5, 0.5, 1)
        if yaxis is None:
            yaxis = Axis(-0.5, 0.5, 1)
        if zaxis is None:
            zaxis = Axis(0.0, 1.0, 1)
        if taxis is None:
            taxis = Axis(0.0, 1.0, 1)

        if xaxis.logscale:
            raise ValueError('Fluence does not support logarithmic x axis!')
        if yaxis.logscale:
            raise ValueError('Fluence does not support logarithmic y axis!')
        if zaxis.logscale:
            raise ValueError('Fluence does not support logarithmic z axis!')
        if taxis.logscale:
            raise ValueError('Fluence does not support logarithmic time axis!')

        self._x_axis = xaxis
        self._y_axis = yaxis
        self._z_axis = zaxis
        self._t_axis = taxis

        self._mode = mode

        self._data = data
        self._nphotons = nphotons

        self._k = k

        if self._x_axis.n*self._y_axis.n*self._z_axis.n*self._t_axis.n <= 0:
            raise ValueError('Fluence accumulator array has one or more array '\
                             'dimensions equal to zero!')

    def _get_nphotons(self) -> int:
        return self._nphotons
    nphotons = property(_get_nphotons, None, None,
                        'The number of photon packets that produced '\
                        'the raw data accumulator content.')

    def _get_mode(self) -> int:
        return self._mode
    mode = property(_get_mode, None, None, 'The accumulator mode.')

    def todict(self) -> dict:
        '''
        Save the fluence configuration without the accumulator data to
        a dictionary.

        Returns
        -------
        data: dict
            Fluence configuration as a dictionary.
        '''
        return {
            'type':'Fluencet',
            'mode':self._mode,
            'xaxis':self._x_axis.todict(),
            'yaxis':self._y_axis.todict(),
            'zaxis':self._z_axis.todict(),
            'taxis':self._t_axis.todict()
        }

    @classmethod
    def fromdict(cls, data: dict) -> 'Fluencet':
        '''
        Create a Fluence instance from a dictionary.

        Parameters
        ----------
        data: dict
            Dictionary created by the :py:meth:`Fluencet.todict` method.
        '''
        data_ = dict(data)
        fluence_type = data_.pop('type')
        if fluence_type != cls.__name__:
            raise TypeError('Expected "{}" type bot got "{}"!'.format(
                cls.__name__, fluence_type))
        x_axis = Axis.fromdict(data_.pop('xaxis'))
        y_axis = Axis.fromdict(data_.pop('yaxis'))
        z_axis = Axis.fromdict(data_.pop('zaxis'))
        t_axis = Axis.fromdict(data_.pop('taxis'))

        return cls(x_axis, y_axis, z_axis, t_axis, **data_)

    def _get_shape(self) -> Tuple[int, int, int, int]:
        return (self._z_axis.n, self._y_axis.n, self._x_axis.n, self._t_axis.n)
    shape = property(_get_shape, None, None, 'Fluence array shape.')

    def _get_x(self) -> np.ndarray:
        return self._x_axis.centers
    x = property(_get_x, None, None, 'Accumulator centers along the x axis.')

    def _get_dx(self) -> np.ndarray:
        return abs(self._x_axis.step)
    dx = property(_get_dx, None, None, 'The size of voxels along the x axis.')

    def _get_y(self) -> np.ndarray:
        return self._y_axis.centers
    y = property(_get_y, None, None, 'Accumulator centers along the y axis.')

    def _get_dy(self) -> np.ndarray:
        return abs(self._y_axis.step)
    dy = property(_get_dy, None, None, 'The size of voxels along the y axis.')

    def _get_z(self) -> np.ndarray:
        return self._z_axis.centers
    z = property(_get_z, None, None, 'Accumulator centers along the z axis.')

    def _get_dz(self) -> np.ndarray:
        return abs(self._z_axis.step)
    dz = property(_get_dz, None, None, 'The size of voxels along the z axis.')

    def _get_t(self) -> np.ndarray:
        return self._t_axis.centers
    t = property(_get_t, None, None, 'Accumulator centers along the t axis.')

    def _get_dt(self) -> np.ndarray:
        return abs(self._t_axis.step)
    dt = property(_get_dt, None, None, 'The size of voxels along the t axis.')

    def _get_x_axis(self) -> Axis:
        return self._x_axis
    xaxis = property(_get_x_axis, None, None,
                     'Accumulator axis object along the x axis.')

    def _get_y_axis(self) -> Axis:
        return self._y_axis
    yaxis = property(_get_y_axis, None, None,
                     'Accumulator axis object along the y axis.')

    def _get_z_axis(self) -> Axis:
        return self._z_axis
    zaxis = property(_get_z_axis, None, None,
                     'Accumulator axis object along the z axis.')

    def _get_t_axis(self) -> Axis:
        return self._t_axis
    taxis = property(_get_t_axis, None, None,
                     'Accumulator axis object along the t axis.')

    def _get_k(self) -> int:
        return self._k
    def _set_k(self, k: int):
        self._k = max(1, min(int(k), int(2**31 - 1)))
    k = property(_get_k, _set_k, None, 'Fluence floating point to accumulator'
                                       'integer conversion coefficient.')

    def _get_raw_data(self) -> np.ndarray:
        return self._data
    def _set_raw_data(self, data: np.ndarray):
        self._data = data
    raw = property(_get_raw_data, _set_raw_data, None,
                   'Raw fluence accumulator data if any.')

    def _get_data(self):
        k = 1.0/(max(self.nphotons, 1)*self.dx*self.dy*self.dz*self.dt)
        return self._data*k
    data = property(_get_data, None, None,
                    'Fluence accumulator - deposition or fluence rate.')

    def update_data(self, mc: mcobject.McObject,
                    data: Dict[np.dtype, List[np.ndarray]],
                    nphotons: int, **kwargs):
        '''
        Update fluence accumulator data with simulation results.

        Parameters
        ----------
        mc: mcobject.McObject
            Simulator instance that produced the data.
        data: Dict[np.dtype, List[np.ndarray]]
            List of allocated accumulators (this implementation uses only
            one accumulator buffer).
        nphotons: int
            The number of photon packets that produced the raw data
            accumulator content.
        kwargs: dict
            Additional keyword arguments not used by this implementation.
        '''
        accumulators = data[np.dtype(mc.types.np_accu)]

        if self._data is not None:
            self._data.flat += accumulators[0]*(1.0/self.k)
            self._nphotons += nphotons
        else:
            self._data = accumulators[0]*(1.0/self.k)
            self._data.shape = self.shape
            self._nphotons = nphotons

    def update(self, obj : 'Fluencet'):
        '''
        Update the fluence accumulator with data from the given fluence object.

        Parameters
        ----------
        obj: Fluencet
            Update the fluence accumulator of this instance with the data
            from fluence instance obj.
        '''
        if self._data is not None:
            if self.shape != obj.shape:
                raise TypeError(
                    'Cannot update with fluence data of incompatible shape!')

            self._data += obj.raw
            self._nphotons += obj.nphotons
        else:
            self._data = obj.raw
            self._nphotons = obj.nphotons

    def cl_pack(self, mc: mcobject.McObject, target: cltypes.Structure = None) \
            -> cltypes.Structure:
        '''
        Fills the structure (target) with the data required by the
        Monte Carlo simulator. See the :py:meth:`Fluencet.cl_type` for a detailed
        list of fields.

        Parameters
        ----------
        mc: mcobject.McObject
            Monte Carlo simulator instance.
        target: ClFluencet
            CStructure that is filled with the source data.
        buffer: np.ndarray
            Accumulator buffer or None. Should be checked for proper size. Use
            py:attr:`mc.types.np_accu` attribute to determine the
            numpy type of the accumulator used in the Monte Carlo simulator.

        Returns
        -------
        target:  ClFluencet
            Filled structure received as an input argument or a new
            instance if the input argument target is None.
        '''
        if target is None:
            target_type = self.cl_type(mc)
            target = target_type()

        allocation = mc.cl_allocate_rw_accumulator_buffer(self, self.shape)
        target.offset = allocation.offset

        target.top_left.x = self._x_axis.start
        target.top_left.y = self._y_axis.start
        target.top_left.z = self._z_axis.start
        target.top_left.w = self._t_axis.start

        target.inv_step.x = 1.0/self._x_axis.step
        target.inv_step.y = 1.0/self._y_axis.step
        target.inv_step.z = 1.0/self._z_axis.step
        target.inv_step.w = 1.0/self._t_axis.step

        target.shape.x = self._x_axis.n
        target.shape.y = self._y_axis.n
        target.shape.z = self._z_axis.n
        target.shape.w = self._t_axis.n

        target.k = self._k

        return target

    def plot(self, scale: str = 'log', axis: str ='z', autoscale: bool = True,
             show: bool = True):
        '''
        Show fluence slices or integral projections.

        Parameters
        ----------
        scale: str
            Data scaling can be "log" for logarithmic or "lin" for linear.
        axis: str
            The axis of slicing ("x", "y" or "z") or a projection along the
            selected coordinate axis ("xproj", "yproj", "zproj").
            Alternatively, specify the projection plane as one of
            ("xy", "xz", or "yz").
        autoscale: bool
            Scale the color coding of individual slices to the corresponding
            range of weights. If True, the color coding changes from slice
            to slice.
        show: bool 
        '''
        from xopto.util import sliceview

        data = self.data

        if axis == 'xy': axis = 'zproj'
        if axis == 'xz': axis = 'yproj'
        if axis == 'yz': axis = 'xproj'

        ax = {'z':0, 'y':1, 'x':2}.get(axis[0], 0)
        logscale = scale == 'log'

        fig = None

        if ax == 0:
            extent = [self._x_axis.start, self._x_axis.stop,
                      self._y_axis.start, self._y_axis.stop]
            slices = self._z_axis.centers
            xlabel, ylabel = 'x', 'y'
        elif ax == 1:
            extent = [self._x_axis.start, self._x_axis.stop,
                      self._z_axis.start, self._z_axis.stop]
            slices = self._y_axis.centers
            xlabel, ylabel = 'x', 'z'
        elif ax == 2:
            extent = [self._y_axis.start, self._y_axis.stop,
                      self._z_axis.start, self._z_axis.stop]
            slices = self._x_axis.centers
            xlabel, ylabel = 'y', 'z'

        window_title = 'Fluence SliceView - {} mode'.format(self.mode)

        if axis in ('xproj', 'yproj', 'zproj'):
            import matplotlib.pyplot as pp

            title = 'Slice {{slice}}/{} @ {} = {{pos:.1f}} ps'.format(
                data.shape[-1], axis)

            data_slice = data.sum(axis=ax)
            low = data_slice.min()

            sv = sliceview.SliceView(
                data_slice, axis=2, slices=self.t*1e12,
                slice_label='Time', slice_valfmt='%.1f ps',
                title=title, logscale=logscale,
                extent=extent, xlabel=xlabel, ylabel=ylabel, origin='lower',
                autoscale=autoscale, aspect='auto')

            sv.fig.canvas.manager.set_window_title(window_title)
            if show:
                pp.show()

        else:
            title = 'Slice {{slice1}}/{} @ {} = {{pos1:.6f}}'.format(
                data.shape[ax], axis)

            sv = sliceview.DualSliceView(
                data,
                axis1=3, slices1=self.t*1e12, slice1_label='Time',
                slice1_valfmt='%.1f ps',
                axis2=ax, slices2=slices, slice2_label='Slice {}'.format(axis),
                title=title, logscale=logscale,
                extent=extent, xlabel=xlabel, ylabel=ylabel, origin='lower',
                autoscale=autoscale, aspect='auto')
            sv.fig.canvas.manager.set_window_title(window_title)
            if show:
                sv.show()

    def __str__(self):
        return "Fluencet(xaxis={}, yaxis={}, zaxis={}, taxis={})".format(
            self._x_axis, self._y_axis, self._z_axis, self._t_axis)

    def __repr__(self):
        return self.__str__() + \
            ' # object at 0x{:>08X}.'.format(id(self))
